"""
Analysis tools
"""
import copy
from datetime import datetime
from typing import List, Union, Dict, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    status, UploadFile,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.forms import Skeleton2UpdateForm
from app.models.mongo import (
    AuditRecordsModel,
    ExperimentModel,
    SkeletonModel2,
    ToolTaskModel,
    UserModel,
)
from app.models.mongo.public_data import PublicDataFileModel
from app.models.mongo import DataFileSystem
from app.schemas import (
    Skeleton2CreateSchema,
    Skeleton2UpdateSchema,
    ToolTaskForSkeletonCreationSchema,
)
from app.usecases import (
    experiments_usecase,
    skeletons_usecase2,
)
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES
from app.utils.file_util import convert_uploaded_img_to_b64_stream_str
from app.utils.middleware_util import get_s3_client
from app.utils.msg_util import creat_message

router = APIRouter()

"""
When updating the tool version：
    - The old version goes offline
    - New version of the content，Publishers can still make changes（as per Releasing new tools）
    - Admin in the background，You can go online at will/Different versions of the offline tool（There may be multiple versions online at the same time）
"""


@router.post("/",
             summary="Analysis tools")
def create_skeleton(
        skeletonCreateSchema: Skeleton2CreateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param skeletonCreateSchema:
    :param current_user:
    :return: ref: `SkeletonSchema`
    """
    # Determine if the experiment came from sharing：If，Is not available
    _code, msg, is_shared = experiments_usecase.check_if_shared_experiment(pk_type='Experiment',
                                                                           pk=skeletonCreateSchema.experiment)
    if _code == status.HTTP_200_OK:
        if is_shared is True:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "The experimental steps come from sharing，Non-releasable tools"})
    else:
        return JSONResponse(status_code=_code, content={"msg": msg})

    # Updating an existing version
    skeleton_renewed_origin = None
    skeletonModel_renewed = None
    skeleton_renewed_id = skeletonCreateSchema.skeleton_renewed
    if skeleton_renewed_id:
        skeletonModel_renewed = SkeletonModel2.objects(id=skeleton_renewed_id).first()
        if not skeletonModel_renewed:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": f"skeleton to renew not found : {skeleton_renewed_id}"})
        else:
            skeleton_renewed_origin = skeletonModel_renewed.skeleton_renewed_origin

    try:
        # experiment
        experiment_id = skeletonCreateSchema.experiment  # str
        experimentModel = ExperimentModel.objects(id=experiment_id).first()
        if not experimentModel:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": f"experiment not found : {experiment_id}"})

        # tasks: List[Dict]
        task_data_list = []
        task_ids = skeletonCreateSchema.experiment_tasks
        if isinstance(task_ids, List) and len(task_ids) > 0:
            for task_id in task_ids:
                tool_task = ToolTaskModel.objects(id=task_id).first()
                if tool_task is None:
                    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        content={"msg": f"tool task not found: {task_id}"})
                else:
                    # task Information
                    task_data = convert_mongo_document_to_data(tool_task)
                    # is_used = False
                    # Note：Adjusting fields, To match Schema
                    task_data["task_id"] = task_data["id"]
                    task_data["task_name"] = task_data["name"]
                    # pop Drop the field that is being adjusted
                    task_data.pop("id", None)
                    task_data.pop("name", None)
                    #
                    task_data = ToolTaskForSkeletonCreationSchema(**task_data,
                                                                  is_used=False).dict()
                    task_data_list.append(task_data)
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid tasks: {skeletonCreateSchema.experiment_tasks}"})

        # experiment_tasks_datasets: List[Dict]
        # Create tools based on datasets Come from “Experimental data”，Store in storage S3，So the frontend just passes the list of objects
        # note：In-memory data produced by the experiment，It is also stored after serialization S3
        dataset_data_list = skeletonCreateSchema.experiment_tasks_datasets
        if not dataset_data_list:
            dataset_data_list = []
        if not isinstance(dataset_data_list, List):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "msg": f"invalid experiment_tasks_datasets: {skeletonCreateSchema.experiment_tasks_datasets}"})
        for dataset_data in dataset_data_list:
            if not isinstance(dataset_data, Dict):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={
                                        "msg": f"invalid experiment_tasks_datasets.dataset: {dataset_data}"})
        # In-memory data processing
        dataset_data_list = skeletons_usecase2.norm_skeleton_experiment_tasks_datasets_for_memory_type(
            dataset_data_list)

        # dag
        dag = skeletonCreateSchema.dag
        inputs = []
        outputs = []
        # traversal dag，Initialization inputs and outputs
        for node in dag:
            if not isinstance(node, Dict):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid dag element: {node}"})
            # inputs
            if node.get("type") == "input" and node.get("checked") is True:
                node_dict = copy.deepcopy(node)
                # inputs append
                inputs.append(node_dict)
                # positioning task
                to_node_id = node_dict.get("to")[0]
                # traversal task Lists
                for task_data in task_data_list:
                    if task_data.get("task_id") == to_node_id:
                        task_inputs = task_data.get("inputs") or []
                        # positioning task.input
                        for _input in task_inputs:
                            if _input.get("name") == node_dict.get("name"):
                                node_dict.update(_input)
                                # Add task_id
                                node_dict['task_id'] = to_node_id
                                node_dict['task_name'] = task_data.get("task_name")
                                # If it's a file/In-memory data/Dataset class：pop off data
                                if (node_dict.get("type") in ["dir", "file"]) or ("datasets" in node_dict.get("type")):
                                    node_dict["data"] = None
                                #
                                break
                        #
                        break
            # outputs
            elif node.get("type") == "output" and node.get("checked") is True:
                node_dict = copy.deepcopy(node)
                # outputs append
                outputs.append(node_dict)
                # positioning task
                from_node_id = None
                for i_node in dag:
                    if i_node.get("type") == "task":
                        to_nodes = i_node.get("to") or []
                        if node.get("id") in to_nodes:
                            from_node_id = i_node.get("id")
                            break
                # traversal task Lists
                for task_data in task_data_list:
                    if task_data.get("task_id") == from_node_id:
                        # Add task_id
                        node_dict['task_id'] = from_node_id
                        node_dict['task_name'] = task_data.get("task_name")
                        #
                        break

        if skeleton_renewed_id and skeletonModel_renewed:
            # New versions of old tools
            skeletonModel = SkeletonModel2(
                id=generate_uuid(length=26),
                skeleton_renewed=skeleton_renewed_id if skeleton_renewed_id else None,
                skeleton_renewed_origin=skeleton_renewed_origin,
                version=skeletonModel_renewed.version,  # Inheriting old tools
                version_meaning=skeletonModel_renewed.version_meaning,  # Inheriting old tools
                user=current_user,
                name=skeletonModel_renewed.name,  # Inheriting old tools
                description=skeletonModel_renewed.description,  # Inheriting old tools
                introduction=skeletonModel_renewed.introduction,  # Inheriting old tools
                logo=skeletonModel_renewed.logo,  # Inheriting old tools
                experiment=experimentModel,
                experiment_tasks=task_data_list,  # List[Dict]
                experiment_tasks_datasets=dataset_data_list,  # List[Dict]
                dag=dag,
                inputs=inputs,
                outputs=outputs,
                inputs_config=skeletonModel_renewed.inputs_config,  # Inheriting old tools
                outputs_config=skeletonModel_renewed.outputs_config,  # Inheriting old tools
                state="UNAPPROVED",
                is_online=False
            )
        else:
            # New tool
            skeletonModel = SkeletonModel2(
                id=generate_uuid(length=26),
                skeleton_renewed=None,
                skeleton_renewed_origin=None,
                version="1.0.0",  # Default initial version
                version_meaning=None,
                user=current_user,
                name=skeletonCreateSchema.name,
                description=skeletonCreateSchema.description,
                introduction=skeletonCreateSchema.introduction,
                logo=None,
                experiment=experimentModel,
                experiment_tasks=task_data_list,  # List[Dict]
                experiment_tasks_datasets=dataset_data_list,  # List[Dict]
                dag=dag,
                inputs=inputs,
                outputs=outputs,
                inputs_config=dict(),
                outputs_config=dict(),
                state="UNAPPROVED",
                is_online=False
            )

        skeletonModel.save()
        skeletonModel.reload()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to create skeleton: {e}"})

    # resp
    data = convert_mongo_document_to_data(skeletonModel)
    # Name of experiment
    experiment_id = data.get("experiment")
    data['experiment_name'] = skeletons_usecase2.get_experiment_name_for_skeleton(experiment_id)

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.get("/",
            summary="Analysis toolsLists")
async def read_skeletons(
        background_tasks: BackgroundTasks,
        name: Union[str, None] = None,
        user_name: Union[str, None] = None,
        state: Union[str, None] = None,
        is_online: Union[bool, None] = None,
        page: int = 0,
        size: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param background_tasks:
    :param name:
    :param user_name:
    :param state:
    :param is_online:
    :param page:
    :param size:
    :param current_user:
    :return:
    """
    # t1 = time.time()
    code, msg, content = await skeletons_usecase2.read_skeletons(
        menu=skeletons_usecase2.MENU_SKELETON,
        background_tasks=background_tasks,
        viewer_id=current_user.id,
        only_own=True,  # See the viewer's own
        name=name,
        user_name=user_name,
        state=state,
        is_online=is_online,
        page=page,
        size=size
    )
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    # t2 = time.time()
    # print(f'read_skeletons: {t2 - t1}')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/{skeleton_id}",
            summary="Analysis tools")
async def read_skeleton(
        skeleton_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param skeleton_id:
    :param current_user:
    :return:
    """
    code, msg, data = await skeletons_usecase2.read_skeleton(skeleton_id=skeleton_id, viewer_id=current_user.id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.get("/optional_inputs/{skeleton_id}/",
            summary="Analysis tools")
async def read_skeleton_optional_inputs(
        skeleton_id: str,
        input_id: str,
        q: Optional[str] = None,
        page: int = 0,
        size: int = 5,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param skeleton_id:
    :param input_id:
    :param q:
    :param page:
    :param size:
    :param current_user:
    :return:
    """
    # SkeletonModel
    skeletonModel = SkeletonModel2.objects(id=skeleton_id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found: {skeleton_id}"})
    #
    optional_inputs = []
    total = 0
    inputs = skeletonModel.inputs
    if isinstance(inputs, List):
        for optional_input in inputs:
            if isinstance(optional_input, Dict) and optional_input.get("id") == input_id:
                # List[Dict]
                optional_inputs = optional_input.get("optional", [])
                # q
                if q is not None:
                    optional_inputs = [i for i in optional_inputs if (isinstance(i.get('name'), str) and str(q) in i.get("name"))]
                # total
                total = len(optional_inputs)
                skip = page * size
                optional_inputs = optional_inputs[skip: skip + size]
                break

    # For each folder/Dataset, Statistical subfile（Level 1）quantity
    client = get_s3_client()
    for optional_input in optional_inputs:
        sub_count = None
        # Dataset
        if isinstance(optional_input.get("data_type"), str) and ("datasets" in optional_input.get("data_type").lower()):
            datasets = optional_input.get("datasets")
            # Only the first layer
            deps = 0
            sub_count = PublicDataFileModel.objects(datasets=datasets, deps=deps).count()
            print(f"datasets: {datasets}")
            print(f"sub_count: {sub_count}")

        elif (optional_input.get("is_dir") is True) or (optional_input.get("is_file") is False):
            bucket_name = optional_input.get("user")
            if len(bucket_name) < 32:
                bucket_name = DataFileSystem.objects(id=optional_input.get("id")).first().user.id
            prefix = f"{optional_input.get('data_path')}/"
            sub_count = len(list(client.list_objects(bucket_name=bucket_name, prefix=prefix)))
        #
        if sub_count is not None:
            optional_input["sub_count"] = sub_count

    resp = {'total': total, 'data': optional_inputs}
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(resp))


@router.put("/intro/{skeleton_id}",
            summary="Analysis toolsUpdate-Information")
async def update_skeleton_intro(
        skeleton_id: str,
        update_form: Skeleton2UpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param skeleton_id:
    :param update_form:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase2.check_if_skeleton_editable(pk=skeleton_id, pk_type='Skeleton')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # SkeletonModel: It has to be yourself.
    skeletonModel = SkeletonModel2.objects(id=skeleton_id,
                                           user=current_user.id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})

    # identifier
    updated = False

    # logo
    logo_file = update_form.logo
    if logo_file:
        logo = convert_uploaded_img_to_b64_stream_str(logo_file.file)
        skeletonModel.logo = logo
        # identifier
        updated = True

    # previews
    previews = []
    preview_files = update_form.previews
    if preview_files:
        for preview_file in preview_files:
            preview = convert_uploaded_img_to_b64_stream_str(preview_file.file)
            previews.append(preview)
        #
        skeletonModel.previews = previews
        # identifier
        updated = True

    # UpdateInformation：Free of logo（file Types）
    updates = {
        "version": update_form.version,
        "version_meaning": update_form.version_meaning,
        "name": update_form.name,
        "description": update_form.description,
        "introduction": update_form.introduction,
        "organization": update_form.organization,
        "developer": update_form.developer,
        "contact_name": update_form.contact_name,
        "contact_email": update_form.contact_email,
        "contact_phone": update_form.contact_phone,
        "statement": update_form.statement
    }
    updates = {k: v for k, v in updates.items() if v not in INVALID_UPDATE_VALUE_TYPES}
    if updates != dict():
        skeletonModel.update(**updates)
        # identifier
        updated = True

    # Update time，And save it
    if updated is True:
        skeletonModel.updated_at = datetime.utcnow()
        skeletonModel.save()

    # UpdateafterInformation
    code, msg, data = await skeletons_usecase2.read_skeleton(skeleton_id=skeleton_id, viewer_id=current_user.id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.put("/config/{skeleton_id}",
            summary="Analysis toolsUpdate-Configuration items")
async def update_skeleton_config(
        skeleton_id: str,
        skeleton_update: Skeleton2UpdateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param skeleton_id:
    :param skeleton_update:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase2.check_if_skeleton_editable(pk=skeleton_id, pk_type='Skeleton')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # SkeletonModel: It has to be yourself.
    skeletonModel = SkeletonModel2.objects(id=skeleton_id,
                                           user=current_user.id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})

    # Update dag after，Update inputs & outputs
    dag = skeleton_update.dag  # List[Dict]
    if dag is not None:
        if isinstance(dag, List) and dag not in INVALID_UPDATE_VALUE_TYPES:
            # Getting initial data
            task_data_list = skeletonModel.experiment_tasks
            inputs_config = skeletonModel.inputs_config
            # Query the last inputs and outputs
            inputs_prev = skeletonModel.inputs
            outputs_prev = skeletonModel.outputs
            # Take the history inputs and outputs，after dag Derived from inputs2 + outputs2 Update
            inputs = []
            outputs = []
            # traversal dag，Initialization inputs and outputs
            for node in dag:
                dag_node = copy.deepcopy(node)
                if not isinstance(dag_node, Dict):
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"msg": f"invalid dag element: {dag_node}"})
                # inputs
                if dag_node.get("type") == "input" and dag_node.get("checked") is True:
                    # note： dag_node existence ['type']，Avoid context coverage
                    dag_node.pop("type", None)
                    # Default
                    node_dict = copy.deepcopy(dag_node)
                    node_data = None
                    # existence inputs_prev，Then the inputs_prev Subject to，In order to node_dict Update
                    input_prev_exist = False
                    if isinstance(inputs_prev, List):
                        for input_prev in inputs_prev:
                            if input_prev.get("id") == dag_node.get("id"):
                                input_prev_exist = True
                                node_data = input_prev.get("data")
                                node_dict = copy.deepcopy(input_prev)
                                node_dict.update(dag_node)
                                break
                    # inputs append
                    inputs.append(node_dict)
                    # positioning task
                    to_node_id = node_dict.get("to")[0]
                    # traversal task Lists
                    for _task_data in task_data_list:
                        task_data = copy.deepcopy(_task_data)
                        if task_data.get("task_id") == to_node_id:
                            task_inputs = task_data.get("inputs") or []
                            # positioning task.input
                            for task_input in task_inputs:
                                if task_input.get("name") == node_dict.get("name"):
                                    # In order to task within input Update; task_input to pop off data
                                    if input_prev_exist is False:
                                        node_data = task_input.get("data")
                                    task_input.pop("data", None)
                                    #
                                    node_dict.update(task_input)
                                    # Add task_id
                                    node_dict['task_id'] = to_node_id
                                    node_dict['task_name'] = task_data.get("task_name")
                                    # If it's a file/In-memory data/datasetsclass：pop off data
                                    if (node_dict.get("type") in ["dir", "file"]) or ("datasets" in node_dict.get("type")):
                                        if isinstance(inputs_config, Dict) and (inputs_config.get("tip") not in [None, "", ' ']):
                                            continue
                                        else:
                                            node_data = None
                                    #
                                    break
                            #
                            break
                    #
                    node_dict["data"] = node_data

                # outputs
                elif dag_node.get("type") == "output" and dag_node.get("checked") is True:
                    # note： dag_node existence ['type']，Avoid context coverage
                    dag_node.pop("type")
                    # Default
                    node_dict = copy.deepcopy(dag_node)
                    # existence inputs_prev，Then the inputs_prev Subject to，In order to node_dict Update
                    if isinstance(outputs_prev, List):
                        for output_prev in outputs_prev:
                            if output_prev.get("id") == dag_node.get("id"):
                                node_dict = copy.deepcopy(output_prev)
                                node_dict.update(dag_node)
                                break
                    # outputs append
                    outputs.append(node_dict)
                    # positioning task
                    from_node_id = None
                    for i_node in dag:
                        if i_node.get("type") == "task":
                            to_nodes = i_node.get("to") or []
                            if dag_node.get("id") in to_nodes:
                                from_node_id = i_node.get("id")
                                break
                    # traversal task Lists
                    for task_data in task_data_list:
                        if task_data.get("task_id") == from_node_id:
                            # Add task_id
                            node_dict['task_id'] = from_node_id
                            node_dict['task_name'] = task_data.get("task_name")
                            #
                            break

            # UpdateInformation
            updates = {
                "dag": dag,
                "inputs": inputs,
                "outputs": outputs,
                "updated_at": datetime.utcnow()
            }
            skeletonModel.update(**updates)
            skeletonModel.save()
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid dag: {dag}"})

    # Update inputs
    inputs = skeleton_update.inputs  # List[Dict]
    if inputs is not None:
        if isinstance(inputs, List) and inputs not in INVALID_UPDATE_VALUE_TYPES:
            for task_input in inputs:
                if not isinstance(task_input, Dict):
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"msg": f"invalid inputs element: {task_input}"})
            #
            skeletonModel.inputs = inputs
            skeletonModel.save()
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid inputs: {inputs}"})
    # Update outputs
    outputs = skeleton_update.outputs  # List[Dict]
    if outputs is not None:
        if isinstance(outputs, List) and outputs not in INVALID_UPDATE_VALUE_TYPES:
            for output in outputs:
                if not isinstance(output, Dict):
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"msg": f"invalid outputs element: {output}"})
            #
            skeletonModel.outputs = outputs
            skeletonModel.save()
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid inputs: {inputs}"})

    # Update inputs_config
    inputs_config = skeleton_update.inputs_config  # Dict
    if inputs_config is not None:
        if isinstance(inputs_config, Dict):
            #
            skeletonModel.inputs_config = inputs_config
            skeletonModel.save()
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid inputs_config: {inputs_config}"})
    # Update outputs_config
    outputs_config = skeleton_update.outputs_config  # Dict
    if outputs_config is not None:
        if isinstance(outputs_config, Dict):
            #
            skeletonModel.outputs_config = outputs_config
            skeletonModel.save()
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid outputs_config: {outputs_config}"})

    # Update
    skeletonModel.save()
    skeletonModel.reload()

    # UpdateafterInformation
    code, msg, data = await skeletons_usecase2.read_skeleton(skeleton_id=skeleton_id, viewer_id=current_user.id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.delete("/{skeleton_id}",
               summary="Analysis toolsDelete")
def delete_skeleton(
        skeleton_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    - Delete Skeleton

    -Tool Publisher，In order toDeleteTools：
        - Judgment state，Of the following circumstances，Delete
            - Not reviewed：UNAPPROVED
            - Failed to pass the audit： DISAPPROVED
        （Once approved,，Whether it's online/Go offline，DeleteandUpdate）

    - Administrator，In order toDeleteTools：
        - Judgment is_online
            - True： Delete
            - False： In order toDelete

    :param skeleton_id:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase2.check_if_skeleton_editable(pk=skeleton_id, pk_type='Skeleton')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # SkeletonModel： It has to be yourself.
    skeletonModel = SkeletonModel2.objects(id=skeleton_id,
                                           user=current_user.id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})
    try:
        # Delete CompoundStep and CompoundStepElement
        skeletonModel.delete()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to delete skeletonModel: {skeleton_id}"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})


@router.post("/audit/{skeleton_id}",
             summary="Analysis tools")
def create_skeleton_audit(
        skeleton_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Creator of the tool，Analysis tools

    :param skeleton_id:
    :param current_user:
    :return:
    """

    # SkeletonModel: It has to be yourself.
    skeletonModel = SkeletonModel2.objects(id=skeleton_id,
                                           user=current_user.id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})

    # Judgment： UNAPPROVED, DISAPPROVED
    state = skeletonModel.state
    if state == "APPROVING":
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"SkeletonModel is now under APPROVING, please wait"})
    if state == "APPROVED":
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"SkeletonModel is already APPROVED"})

    # Update，It has to be yourself.
    skeletonModel.state = "APPROVING"
    skeletonModel.updated_at = datetime.utcnow()
    skeletonModel.save()
    skeletonModel.reload()
    #
    try:

        audit_records = AuditRecordsModel(id=generate_uuid(),
                                          applicant=current_user,
                                          audit_result="Pending review",
                                          component=skeletonModel,
                                          audit_type="Tools",
                                          )
        audit_records.save()
        creat_message(user=current_user, message_base=audit_records)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Analysis tools!"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})
