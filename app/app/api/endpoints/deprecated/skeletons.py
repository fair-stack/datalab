"""
Deprecated:
Analysis tools
"""
from datetime import datetime
from typing import List, Union, Dict

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.forms.deprecated import SkeletonUpdateForm
from app.models.mongo import (
    AuditRecordsModel,
    ExperimentModel,
    ToolTaskModel,
    UserModel,
)
from app.models.mongo.deprecated import SkeletonModel
from app.schemas import ToolTaskForSkeletonCreationSchema
from app.schemas.deprecated import SkeletonCreateSchema
from app.usecases import experiments_usecase
from app.usecases.deprecated import skeletons_usecase
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES
from app.utils.file_util import convert_uploaded_img_to_b64_stream_str
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
        skeletonCreateSchema: SkeletonCreateSchema,
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
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": "The experimental steps come from sharing，Non-releasable tools"})
    else:
        return JSONResponse(status_code=_code, content={"msg": msg})

    # Determine whether to update an existing version
    skeleton_renewed_id = skeletonCreateSchema.skeleton_renewed
    skeleton_renewed_origin = None
    if skeleton_renewed_id:
        skeletonModel_renewed = SkeletonModel.objects(id=skeleton_renewed_id).first()
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
        dataset_data_list = skeletons_usecase.norm_skeleton_experiment_tasks_datasets_for_memory_type(dataset_data_list)

        # Fetching dependencies
        code, msg, dependencies_data = skeletons_usecase.get_tool_tasks_dependencies(task_ids)
        if code != status.HTTP_200_OK:
            return JSONResponse(status_code=code,
                                content={"msg": msg})

        skeletonModel = SkeletonModel(
            id=generate_uuid(length=26),
            skeleton_renewed=skeleton_renewed_id if skeleton_renewed_id else None,
            skeleton_renewed_origin=skeleton_renewed_origin,
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
            experiment_tasks_dependencies=dependencies_data,
            compoundsteps=[],  # Initially, is []
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

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.get("/",
            summary="Analysis tools")
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
    code, msg, content = await skeletons_usecase.read_skeletons(
        menu=skeletons_usecase.MENU_SKELETON,
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
    code, msg, data = await skeletons_usecase.read_skeleton(skeleton_id=skeleton_id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.put("/{skeleton_id}",
            summary="Analysis tools")
async def update_skeleton(
        skeleton_id: str,
        skeleton_update_form: SkeletonUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param skeleton_id:
    :param skeleton_update_form:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase.check_if_skeleton_editable(pk=skeleton_id, pk_type='Skeleton')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # SkeletonModel: It has to be yourself.
    skeletonModel = SkeletonModel.objects(id=skeleton_id,
                                          user=current_user.id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})

    # identifier
    updated = False

    # logo
    logo_file = skeleton_update_form.logo
    if logo_file:
        # storage_path = Path(settings.BASE_DIR, settings.SKELETON_PATH, skeleton_id)
        # if not (storage_path.exists() and storage_path.is_dir()):
        #     storage_path.mkdir(parents=True)
        #
        # dest_path = Path(storage_path, logo_file.filename)
        # # As the name file exists，Then it covers
        # # file.file is `file-like` object
        # chunked_copy(logo_file.file, dest_path)
        logo = convert_uploaded_img_to_b64_stream_str(logo_file.file)
        # skeletonModel.logo = str(dest_path.resolve())
        skeletonModel.logo = logo
        # identifier
        updated = True

    # Information：Free of logo（file Types）
    updates = {
        "version": skeleton_update_form.version,
        "version_meaning": skeleton_update_form.version_meaning,
        "name": skeleton_update_form.name,
        "description": skeleton_update_form.description,
        "introduction": skeleton_update_form.introduction
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

    # Information
    code, msg, data = await skeletons_usecase.read_skeleton(skeleton_id=skeleton_id)
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

    -Tool Publisher，DeleteTools：
        - Judgment state，Of the following circumstances，Delete
            - Not reviewed：UNAPPROVED
            - Failed to pass the audit： DISAPPROVED
        （Once approved,，Whether it's online/Go offline，Delete）

    - Administrator，DeleteTools：
        - Judgment is_online
            - True： Delete
            - False： Delete

    :param skeleton_id:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase.check_if_skeleton_editable(pk=skeleton_id, pk_type='Skeleton')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # SkeletonModel： It has to be yourself.
    skeletonModel = SkeletonModel.objects(id=skeleton_id,
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
    skeletonModel = SkeletonModel.objects(id=skeleton_id,
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

    # Updating state，It has to be yourself.
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
