from datetime import datetime
from typing import Union, List

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.models.mongo import (
    ExperimentModel,
    ToolTaskModel,
    UserModel,
    XmlToolSourceModel,
)
from app.schemas import (
    convertSchemaExptBaseToExptInDB,
    ExperimentBaseSchema,
    ExperimentBatchDeleteSchema,
    ExperimentUpdateSchema,
    ExperimentInDBSchema,
    ToolTaskBaseSchema,
)
from app.usecases import experiments_usecase
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES

router = APIRouter()


@router.post("/",
             response_model=ExperimentInDBSchema,
             summary="Experiment Creation")
def create_experiment(
        expt: ExperimentBaseSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    try:
        exptInDBSchema = convertSchemaExptBaseToExptInDB(expt, user=current_user.id)
        exptModel = ExperimentModel(**exptInDBSchema.dict())
        exptModel.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": "failed to create experiment"})

    return exptInDBSchema


@router.put("/{expt_id}",
            response_model=ExperimentInDBSchema,
            summary="Experimental modifications")
def update_experiment(
        expt_id: str,
        expt_update: ExperimentUpdateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    # Determine if the experiment came from sharing：If，Is not editable
    _code, msg, is_shared = experiments_usecase.check_if_shared_experiment(pk_type='Experiment', pk=expt_id)
    if _code == status.HTTP_200_OK:
        if is_shared is True:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": "Experiment from Share，Not editable"})
    else:
        return JSONResponse(status_code=_code, content={"msg": msg})

    exptModel = ExperimentModel.objects(id=expt_id, user=current_user).first()
    if exptModel is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "experiment not found"})
    try:
        updates = {k: v for k, v in expt_update.dict().items() if v not in INVALID_UPDATE_VALUE_TYPES}
        if bool(updates):
            updates["updated_at"] = datetime.utcnow()
            exptModel.update(**updates)
            # Must reload to get updated attribute
        exptModel.save()
        exptModel.reload()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": "failed to update experiment"})
    else:
        data = convert_mongo_document_to_data(exptModel)
        exptInDBSchema = ExperimentInDBSchema(**data)
        return exptInDBSchema


@router.get("/",
            summary="List of experiments (Trial run experiments are not included)")
def read_experiments(
        is_shared: Union[bool, None] = None,
        name: Union[str, None] = None,
        creator: Union[str, None] = None,
        page: int = 0,
        size: int = 10,
        sort: str = 'desc',
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    NOTE： Experiments during the trial run are not shown (is_trial=True)

    :param is_shared:
    :param name:
    :param creator:
    :param page:
    :param size:
    :param sort:
    :param current_user:
    :return:
    """
    content = experiments_usecase.read_experiments(
        is_shared=is_shared,
        name=name,
        creator=creator,
        page=page,
        size=size,
        viewer=current_user,
        only_own=True,  # You can only see your own
        sort=sort
    )

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/{expt_id}",
            summary="Details of the experiment")
def read_experiment(
        expt_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):

    exptModel = ExperimentModel.objects(id=expt_id).first()

    if exptModel is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "experiment not found"})

    data = convert_mongo_document_to_data(exptModel)
    exptInDBSchema = ExperimentInDBSchema(**data)

    tool_task_ids = exptInDBSchema.tasks
    if tool_task_ids is None:
        tool_task_ids = []

    task_data_list = []
    for task_id in tool_task_ids:
        tool_task = ToolTaskModel.objects(id=task_id).first()
        if tool_task is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": f"tool task not found: {task_id}"})
        else:
            # task Information
            task_data = convert_mongo_document_to_data(tool_task)
            task_data = ToolTaskBaseSchema(**task_data).dict()
            # task Corresponding to tool Information
            try:
                if tool_task.tool is None:
                    tool_info = None
                else:
                    tool_data = convert_mongo_document_to_data(tool_task.tool)
                    # Just take the basics tool Information（schema Filtering）
                    tool_info = {
                        'id': tool_data.get("id"),
                        'name': tool_data.get("name"),
                        'status': tool_data.get("status")
                    }
            except Exception as e:
                print(f"read_experiment: {e}")
                tool_info = None

            task_data['tool_info'] = tool_info
            task_data_list.append(task_data)

    content = {"msg": "success",
               # "expt": exptInDBSchema.dict(),
               "expt": data,
               "tasks": task_data_list}

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.delete("/{expt_id}",
               summary="Experiment deletion")
def delete_experiment(
        expt_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):

    exptModel = ExperimentModel.objects(id=expt_id, user=current_user).first()

    if exptModel is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "experiment not found"})

    try:
        exptModel.delete()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to delete experiment: [{expt_id}]"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success"})


@router.delete("/",
               summary="Experiment deletion（Batch size）")
def delete_experiments(
        batch_schema: ExperimentBatchDeleteSchema,
        current_user: UserModel = Depends(deps.get_current_user)):
    ids = batch_schema.ids
    if isinstance(ids, list):
        for expt_id in ids:
            exptModel = ExperimentModel.objects(id=expt_id).first()

            if exptModel is None:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                    content={"msg": "experiment not found"})

            try:
                exptModel.delete()
            except Exception as e:
                print(e)
                return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    content={"msg": f"failed to delete experiment: [{expt_id}]"})
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success"})
    else:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "invalid ids"})


@router.post("/copy/{expt_id}",
             response_model=ExperimentInDBSchema,
             summary="Replication of experiments")
def copy_experiment(
        expt_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Replication of experiments：

        - Name of experiment： experiment -> experiment_copy
        - Step replication：
            - task New： user for current_user
            - Based on the same tool
            - inputs：Copying variable names + Parameter values data
            - outputs：Copying variable names，Not copying values data

    :param expt_id:
    :param current_user:
    :return:
    """
    # You can only run your own experiments
    exptModel = ExperimentModel.objects(id=expt_id,
                                        user=current_user).first()

    if exptModel is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "experiment not found"})

    # No copying trial Types
    is_trial = exptModel.is_trial
    if is_trial is True:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "trial experiment not permit for copy"})

    # New Experiment
    try:
        exptModel_2 = ExperimentModel(
            id=generate_uuid(length=26),
            name=f"{exptModel.name}_copy",      # name Appending characters `_copy`
            description=exptModel.description,
            user=current_user,
            tasks=[]    # Temporarily vacant，Subsequent additions
        )
        exptModel_2.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to copy experiment: {e}"})

    # Obtaining experimental data
    data = convert_mongo_document_to_data(exptModel)
    exptInDBSchema = ExperimentInDBSchema(**data)

    tool_task_ids = exptInDBSchema.tasks
    if tool_task_ids is None:
        tool_task_ids = []

    new_task_ids = []
    for task_id in tool_task_ids:
        tool_task = ToolTaskModel.objects(id=task_id).first()
        if tool_task is None:
            # Delete established experiments
            exptModel_2.delete()
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": f"tool task not found: {task_id}"})
        else:
            tool_task_data = convert_mongo_document_to_data(tool_task)

            # Lookup tool
            tool_id = tool_task_data.get("tool")
            # tool_id Is equal to None
            #   - YES：Indicates that the component has not been added, allow
            #   - NO: Corresponding to toolModel Does it exist： If it doesn't exist，allow，Back to Tips
            if tool_id is None:
                toolModel = None
            else:
                toolModel = XmlToolSourceModel.objects(id=tool_id).first()
                if not toolModel:
                    # Delete established experiments
                    exptModel_2.delete()
                    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        content={"msg": f"Component does not exist [{tool_id}]，Unable to replicate experiments"})

            # inputs & outputs
            inputs = tool_task_data.get("inputs", list())
            outputs = tool_task_data.get("outputs", list())
            # inputs preprocessing
            if isinstance(inputs, List):
                for _input in inputs:
                    # Get rid of `data`
                    _input.pop("data", None)
                    # Get rid ofInformation： {"_cls": xxx}
                    _input.pop("_cls", None)
            else:
                # Delete established experiments
                exptModel_2.delete()
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid inputs for tool task: {task_id}"})
            # outputs preprocessing
            if isinstance(outputs, List):
                for output in outputs:
                    # Get rid of `data`
                    output.pop("data", None)
                    # Get rid ofInformation： {"_cls": xxx}
                    output.pop("_cls", None)
            else:
                # Delete established experiments
                exptModel_2.delete()
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid outputs for tool task: {task_id}"})
            # New task
            new_task = ToolTaskModel(
                id=generate_uuid(length=26),
                name=tool_task_data.get("name"),
                description=tool_task_data.get("description"),
                tool=toolModel,
                experiment=exptModel_2,
                user=current_user,
                inputs=inputs,
                outputs=outputs
            )
            new_task.save()
            new_task.reload()
            #
            new_task_ids.append(new_task.id)
    # Update tasks
    exptModel_2.tasks = new_task_ids
    exptModel_2.save()
    exptModel_2.reload()
    # Reading data
    data = convert_mongo_document_to_data(exptModel_2)
    exptInDBSchema = ExperimentInDBSchema(**data)
    return exptInDBSchema


@router.post("/share/{expt_id}",
             response_model=ExperimentInDBSchema,
             summary="Experiment Sharing")
def share_experiment(
        expt_id: str,
        to_user: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Experiment Sharing

    :param expt_id:
    :param to_user:
    :param current_user:
    :return:
    """
    to_user_Model = UserModel.objects(id=to_user).first()

    if to_user_Model is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "user not found"})

    # You can only run your own experiments
    exptModel = ExperimentModel.objects(id=expt_id,
                                        user=current_user).first()

    if exptModel is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "experiment not found"})

    # No sharing trial Types
    is_trial = exptModel.is_trial
    if is_trial is True:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "trial experiment not permit for sharing"})

    # No sharing
    is_shared = exptModel.is_shared
    if is_shared is True:
        # return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": "shared experiment not permit for further sharing"})
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Experiments shared by others，No further sharing"})

    # New Experiment
    try:
        exptModel_2 = ExperimentModel(
            id=generate_uuid(length=26),
            is_shared=True,
            shared_from_experiment=exptModel,
            name=exptModel.name,
            description=exptModel.description,
            user=to_user_Model,
            tasks=[]    # Temporarily vacant，Subsequent additions
        )
        exptModel_2.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to copy experiment: {e}"})

    # Obtaining experimental data
    data = convert_mongo_document_to_data(exptModel)
    exptInDBSchema = ExperimentInDBSchema(**data)

    tool_task_ids = exptInDBSchema.tasks
    if tool_task_ids is None:
        tool_task_ids = []

    new_task_ids = []
    for task_id in tool_task_ids:
        tool_task = ToolTaskModel.objects(id=task_id).first()
        if tool_task is None:
            # Delete established experiments
            exptModel_2.delete()
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": f"tool task not found: {task_id}"})
        else:
            tool_task_data = convert_mongo_document_to_data(tool_task)

            # Lookup tool
            tool_id = tool_task_data.get("tool")
            # tool_id Is equal to None
            #   - YES：Indicates that the component has not been added, allow
            #   - NO: Corresponding to toolModel Does it exist： If it doesn't exist，allow，Back to Tips
            if tool_id is None:
                toolModel = None
            else:
                toolModel = XmlToolSourceModel.objects(id=tool_id).first()
                if not toolModel:
                    # Delete established experiments
                    exptModel_2.delete()
                    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                        content={"msg": f"Component does not exist [{tool_id}]，Unable to share experiments"})
            # inputs & outputs
            inputs = tool_task_data.get("inputs")
            outputs = tool_task_data.get("outputs")
            # inputs preprocessing
            if isinstance(inputs, List):
                for _input in inputs:
                    # Hold on `data`
                    # _input.pop("data", None)
                    # Get rid ofInformation： {"_cls": xxx}
                    _input.pop("_cls", None)
            else:
                # Delete established experiments
                exptModel_2.delete()
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid inputs for tool task: {task_id}"})
            # outputs preprocessing
            if isinstance(outputs, List):
                for output in outputs:
                    # Hold on `data`
                    # output.pop("data", None)
                    # Get rid ofInformation： {"_cls": xxx}
                    output.pop("_cls", None)
            else:
                # Delete established experiments
                exptModel_2.delete()
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid outputs for tool task: {task_id}"})
            # New task
            new_task = ToolTaskModel(
                id=generate_uuid(length=26),
                name=tool_task_data.get("name"),
                description=tool_task_data.get("description"),
                tool=toolModel,
                experiment=exptModel_2,
                user=to_user_Model,
                inputs=inputs,
                outputs=outputs
            )
            new_task.save()
            new_task.reload()
            #
            new_task_ids.append(new_task.id)
    # Update tasks
    exptModel_2.tasks = new_task_ids
    exptModel_2.save()
    exptModel_2.reload()
    # Reading data
    data = convert_mongo_document_to_data(exptModel_2)
    exptInDBSchema = ExperimentInDBSchema(**data)
    return exptInDBSchema
