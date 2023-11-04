from datetime import datetime

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
    ToolSourceBaseSchema,
    ToolTaskCreateSchema,
    ToolTaskCreatedSchema,
    ToolTaskSchema,
    ToolTaskUpdateSchema,
)
from app.usecases import experiments_usecase
from app.utils.common import generate_uuid, convert_mongo_document_to_data
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES

router = APIRouter()


@router.post("/",
             response_model=ToolTaskCreatedSchema,
             summary="Experiment component task creation")
def create_task(
        tool_task_create: ToolTaskCreateSchema,
        current_user: UserModel = Depends(deps.get_current_user)):
    """"""

    # Getting parameters: Experiment id
    experiment_id = tool_task_create.experiment_id
    expt = ExperimentModel.objects(id=experiment_id,
                                   user=current_user.id).first()
    if expt is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "experiment not found"})

    # Create tool task
    try:
        toolTaskSchema = ToolTaskSchema(**tool_task_create.dict(),
                                        id=generate_uuid(length=26),
                                        experiment=experiment_id,
                                        user=current_user.id)
        toolTaskModel = ToolTaskModel(**toolTaskSchema.dict())
        toolTaskModel.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to create task for experiment: {experiment_id}"})

    # Updating the component list
    try:
        task_id_list = expt.tasks
        if task_id_list is None:
            task_id_list = []
        task_id_list.append(toolTaskSchema.id)
        # Updating fields `tasks`
        expt.tasks = task_id_list
        expt.updated_at = datetime.utcnow()
        expt.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={
                                "msg": f"failed to add tool task [{toolTaskSchema.id}] to experiment [{experiment_id}]"})
    else:
        # packing
        toolTaskCreatedSchema = ToolTaskCreatedSchema(
            experiment_id=experiment_id,
            tool_task_id=toolTaskSchema.id
        )
        return toolTaskCreatedSchema


@router.get("/",
            summary="ExperimentLists")
def read_tasks(
        page: int = 0,
        size: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)):
    """"""
    skip = page * size
    total = ToolTaskModel.objects(user=current_user.id).count()
    # [] if not exists
    tool_tasks = ToolTaskModel.objects(user=current_user.id).order_by("-created_at")[skip: skip + size]

    data = []
    for tool_task in tool_tasks:
        # task Information
        task_data = convert_mongo_document_to_data(tool_task)
        # task Corresponding to tool Information
        try:
            if tool_task.tool is None:
                tool_info = None
            else:
                tool_data = convert_mongo_document_to_data(tool_task.tool)
                # Just take the basics tool Information（schema Filtering）
                tool_info = ToolSourceBaseSchema(**tool_data).dict()
        except Exception as e:
            print(f"read_tasks: {e}")
            tool_info = None

        task_data["tool_info"] = tool_info
        # append
        data.append(task_data)
    # packing
    content = {"msg": "success",
               "total": total,
               "data": data}

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/{task_id}",
            summary="Experiment")
def read_task(
        task_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """"""

    tool_task = ToolTaskModel.objects(id=task_id).first()
    if tool_task is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"tool task not found: [{task_id}]"})
    # task Information
    task_data = convert_mongo_document_to_data(tool_task)
    # task Corresponding to tool Information
    try:
        if tool_task.tool is None:
            tool_info = None
        else:
            tool_data = convert_mongo_document_to_data(tool_task.tool)
            # Just take the basics tool Information（schema Filtering）
            tool_info = ToolSourceBaseSchema(**tool_data).dict()
    except Exception as e:
        print(f"read_task: {e}")
        tool_info = None

    task_data["tool_info"] = tool_info
    content = {"msg": "success",
               "data": task_data}
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.put("/{task_id}",
            summary="Experiment")
def update_task(
        task_id: str,
        task_update: ToolTaskUpdateSchema,
        current_user: UserModel = Depends(deps.get_current_user)):

    # JudgmentExperiment：If，Is not editable
    _code, msg, is_shared = experiments_usecase.check_if_shared_experiment(pk_type='Task', pk=task_id)
    if _code == status.HTTP_200_OK:
        if is_shared is True:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": "Experiment，Not editable"})
    else:
        return JSONResponse(status_code=_code, content={"msg": msg})

    # Judgment task existence
    tool_task = ToolTaskModel.objects(id=task_id).first()
    if tool_task is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"tool task not found: [{task_id}]"})

    # Exclude invalid key
    updates = {k: v for k, v in task_update.dict().items() if v not in INVALID_UPDATE_VALUE_TYPES}

    # existence tool_id：New components，or Replacement of components
    # Judgmentexistence
    tool_id = task_update.tool_id
    if tool_id is not None:
        tool = XmlToolSourceModel.objects(id=tool_id).first()
        if tool is None:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid tool_id [{tool_id}], corresponding tool not found"})
        else:
            tool_task.tool = tool
            # will tool the inputs/outputs Copy to task the inputs/outputs
            tool_data = convert_mongo_document_to_data(tool_task.tool)
            tool_task.inputs = tool_data.get("inputs", None)
            tool_task.outputs = tool_data.get("outputs", None)
            tool_task.updated_at = datetime.utcnow()

    try:
        # Get rid of tool_id， Because field The name is tool
        updates.pop("tool_id", None)
        if bool(updates):
            updates["updated_at"] = datetime.utcnow()
            tool_task.update(**updates)
        tool_task.save()
        # Must reload to get updated attributes
        tool_task.reload()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to update tool task: [{task_id}]"})
    else:
        # task Information
        task_data = convert_mongo_document_to_data(tool_task)
        # task Corresponding to tool Information
        try:
            if tool_task.tool is None:
                tool_info = None
            else:
                tool_data = convert_mongo_document_to_data(tool_task.tool)
                # Just take the basics tool Information（schema Filtering）
                tool_info = ToolSourceBaseSchema(**tool_data).dict()
        except Exception as e:
            print(f"update_task: {e}")
            tool_info = None

        task_data["tool_info"] = tool_info
        content = {"msg": "success",
                   "data": task_data}
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=jsonable_encoder(content))


@router.delete("/{task_id}",
               summary="Experiment")
def delete_task(
        task_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):

    # JudgmentExperiment：If，Is not editable
    _code, msg, is_shared = experiments_usecase.check_if_shared_experiment(pk_type='Task', pk=task_id)
    if _code == status.HTTP_200_OK:
        if is_shared is True:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": "Experiment，Non-deletable"})
    else:
        return JSONResponse(status_code=_code, content={"msg": msg})

    # Judgment task existence
    tool_task = ToolTaskModel.objects(id=task_id).first()
    if tool_task is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"tool task not found: [{task_id}]"})

    # Corresponding to Experiment
    experiment = tool_task.experiment
    if experiment is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"corresponding experiment not found for task: [{task_id}]"})

    # experiment the tasks Lists，Corresponding to task_id
    task_id_list = experiment.tasks

    # Experiment the tasks Invalid
    if bool(task_id_list) is False or not isinstance(task_id_list, list):
        # delete dangling Task
        tool_task.delete()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid tasks of experiment corresponding to task [{task_id}] "})
    # Be absent Experiment the tasks Lists
    if task_id not in task_id_list:
        # delete irrelevant Task
        tool_task.delete()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"task [{task_id}] not found in corresponding experiment tasks"})
    else:
        # Get rid of Experiment the tasks Lists
        try:
            task_id_list.remove(task_id)
            experiment.tasks = task_id_list
            experiment.updated_at = datetime.utcnow()
            experiment.save()
            tool_task.delete()
        except Exception as e:
            print(e)
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                content={"msg": f"failed to delete task: [{task_id}]"})
        else:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"msg": "success"})
