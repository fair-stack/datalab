from typing import Union, Optional
from datetime import datetime
import os
import shutil
import uuid
from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.api import deps
from app.models.mongo import (
    UserModel,
    ExperimentModel,
    ToolTaskModel,
    ToolsTreeModel,
    AuditRecordsModel,
    XmlToolSourceModel,
    ComponentInstance,
    VisualizationComponentModel,
)
from app.models.mongo.fair import FairMarketComponentsModel
from app.schemas import (
    ExperimentInDBSchema,
    TrialExperimentSchema,
    ToolTaskBaseSchema,
    ToolsTreeSchema,
    ToolsTreeResponseSchema,
    AuditRecordsSchema,
    ToolSourceBaseSchema


)
from app.core.config import settings
from app.schemas.experiment import convertSchemaTrialExptToExptInDB
from app.usecases import tools_usecase
from app.utils.common import convert_mongo_document_to_schema, convert_mongo_document_to_data


router = APIRouter()


"""
Two types of components：  
    - Analysis class
    - Visualization class: TODO
"""


@router.get("/visualization", summary="Whereas class components-Lists")
async def read_visualization_tools(skip: int = 0,
                                    limit: int = 10,
                                    state: Optional[bool] = None,
                                    current_user: UserModel = Depends(deps.get_current_user)):
    skip = skip * limit
    if state is not None:
        objects = VisualizationComponentModel.objects(enable=state).order_by('-create_at')
    else:
        objects = VisualizationComponentModel.objects().order_by('-create_at')
    data = list()
    _disable = VisualizationComponentModel.objects(enable=False).count()
    _enable = VisualizationComponentModel.objects(enable=True).count()
    _all = VisualizationComponentModel.objects().count()
    for i in objects:
        item = i.to_mongo().to_dict()
        if isinstance(i.source, FairMarketComponentsModel):
            item['source'] = "Software markets expose components"
            item['user'] = i.source.authorName
        else:
            item['source'] = "User-uploaded components"
            item['user'] = i.source.user.name
        item['source_id'] = i.source.id
        item['create_at'] = i.create_at.strftime('%Y/%m/%d %H:%M:%S')
        item['update_at'] = i.update_at.strftime('%Y/%m/%d %H:%M:%S')
        data.append(item)

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            "data": data[skip: skip+limit],
                            "total": len(data),
                            "all_counts": _all,
                            "enable_counts": _enable,
                            "disable_counts": _disable
                                 }
                        )


@router.put('/visualization/state', summary="Disable/Enable a visualization component")
async def update_visualization_tool_state(tool_id: str,
                                          state: bool,
                                          current_user: UserModel = Depends(deps.get_current_user)):
    tool_model = VisualizationComponentModel.objects(id=tool_id).first()
    if tool_model is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Malicious explosion library tamper with data？"})
    if tool_model.enable is state:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Visual components<{tool_model.name}>"
                                            f"Currently is{ 'Enabled status' if tool_model.enable is True else 'Disable'}"})
    tool_model.update(enable=state)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.get("/analysis/tree",
            summary="Analysis classComponents-Tree pattern")
def read_tools(
        state: Optional[Union[bool, str]] = '',
        audit: Optional[str] = '',
        current_user: UserModel = Depends(deps.get_current_user)):
    data = tools_usecase.read_tools_in_tree_format(state=state, audit=audit)
    content = {
        'msg': "success",
        'data': data
    }
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.post('/analysis/list',
             summary="Analysis classComponents-Table schema")
def get_components(
        skip: int = 0,
        limit: int = 10,
        query_sets: dict = {},
        current_user: UserModel = Depends(deps.get_current_user)):
    tool_list = list()
    online = 0
    offline = 0
    all_tools = 0
    skip = skip * limit
    if query_sets.get('name'):
        name = query_sets.pop('name')
        xml_model = XmlToolSourceModel.objects(**query_sets).filter(
            __raw__={'name': {'$regex': f'.*{name}'}})
    else:
        xml_model = XmlToolSourceModel.objects(**query_sets)

    for i in xml_model:
        _tool = convert_mongo_document_to_schema(i, ToolSourceBaseSchema)
        _tool['author'] = i.user.name
        if query_sets.get("status") is None:
            tool_list.append(_tool)
        else:
            tool_list.append(_tool)
        if i.status is True:
            online += 1
        else:
            offline += 1
        all_tools += 1
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": 'Success', "data": tool_list[skip: skip + limit],
                                 "total": all_tools,
                                 "online": online,
                                 "offline": offline})


@router.get('/{component_name}',
            summary='Component Details')
def get_component(component_name: str,
                  current_user: UserModel = Depends(deps.get_current_user)):
    try:
        if component_name.endswith('-id'):
            component_name = component_name.replace('-id', '')
            _data = convert_mongo_document_to_schema(XmlToolSourceModel.objects(id=component_name).first(),
                                                     ToolSourceBaseSchema)
        else:
            _data = convert_mongo_document_to_schema(XmlToolSourceModel.objects(name=component_name).first(),
                                                     ToolSourceBaseSchema)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": 'Success', "data": [_data]})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": 'Success', "data": list()})


@router.delete('/{component_id}',
               summary="Component removal")
def delete_component(component_id: str,
                     current_user: UserModel = Depends(deps.get_current_user)):
    try:

        tool_objs = XmlToolSourceModel.objects(id=component_id).first()
        shutil.rmtree(tool_objs.folder_path)
        os.remove(tool_objs.folder_path.replace('storage_tools', 'storage_tools_zips') + '.zip')
        tool_objs.delete()
        ComponentInstance.objects(base_id=component_id).first().delete()
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.get('/runtime/env')
def get_all_env(current_user: UserModel = Depends(deps.get_current_user)):
    env_list = XmlToolSourceModel.objects.exclude('language').distinct('language')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": 'Success', "data": env_list})


@router.put('/{component_id}',
            summary="Component editing")
def update_component(component_id: str,
                     update_set: dict,
                     current_user: UserModel = Depends(deps.get_current_user)
                     ):
    try:
        if update_set.get('audit'):
            update_set.pop('audit')
        XmlToolSourceModel.objects(id=component_id).update_one(**update_set)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.post("/trials/",
             summary="Component trial run creation")
def create_trial_experiment(
        trial: TrialExperimentSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):

    trialExpt = ExperimentModel.objects(trial_tool_id=trial.trial_tool_id).first()
    # It already exists
    if trialExpt:
        data = convert_mongo_document_to_data(trialExpt)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success: already exist",
                                     "data": jsonable_encoder(data)})

    try:
        exptInDBSchema = convertSchemaTrialExptToExptInDB(trial, user=current_user.id)
        exptModel = ExperimentModel(**exptInDBSchema.dict())
        exptModel.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": "failed to create trial experiment"})
    else:
        data = exptInDBSchema.dict()
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success: created",
                                     "data": jsonable_encoder(data)})


@router.get("/trials/{expt_id}",
            summary="Component trial run details")
def read_trial_experiment(
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
                print(f"read_trial_experiment: {e}")
                tool_info = None

            task_data['tool_info'] = tool_info
            task_data_list.append(task_data)

    content = {"msg": "success",
               "expt": exptInDBSchema.dict(),
               "tasks": task_data_list}

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.put('/audit/{component_id}',
            summary="Component auditing")
def audit_component(component_id: str,
                    audit: str,
                    info: str = '',
                    current_user: UserModel = Depends(deps.get_current_user)
                     ):
    try:
        if audit not in settings.AUDIT_ALLOW:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": "Malicious approval"})

        XmlToolSourceModel.objects(id=component_id).update_one(audit=audit, audit_info=info)
        AuditRecordsModel.objects(component=XmlToolSourceModel.objects(id=component_id).first()).update_one(audit_result=audit, audit_at=datetime.utcnow,
                                                                          audit_info=info, auditor=current_user)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.put('/audit/submit/{component_id}')
def component_audit_submit(component_id: str,
                           update_set: dict,
                           current_user: UserModel = Depends(deps.get_current_user)):
    try:
        audit_id = str(uuid.uuid4())
        update_set['audit'] = "Pending review"
        applicant = current_user
        content = update_set['name']
        tool_source = XmlToolSourceModel.objects(id=component_id)
        tool_source.update_one(**update_set)
        audit_records = AuditRecordsModel(id=audit_id, applicant=applicant, content=content, audit_result="Pending review",
                                          component=tool_source.first())
        audit_records.save()
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.get('/audit/info')
def audit_info(
        audit_type: str = None,
        skip: int = 0,
        limit: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)):
    skip = skip * limit
    if audit_type:
        _d = AuditRecordsModel.objects(audit_result=audit_type, audit_type="Components")
    else:
        _d = AuditRecordsModel.objects(audit_type="Components")
    _d = _d.order_by("-audit_at")
    _data = list(map(lambda x: convert_mongo_document_to_schema(x, AuditRecordsSchema,
                                                                revers_map=['applicant', 'auditor', 'component']), _d))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success",
                                 "data": _data[skip: skip+limit],
                                 "total": len(_data)})


@router.post('/audit/info')
def audit_info(
        audit_type: str = None,
        skip: int = 0,
        limit: int = 10,
        name: str = None,
        current_user: UserModel = Depends(deps.get_current_user)):
    skip = skip * limit
    if audit_type:
        _d = AuditRecordsModel.objects(audit_result=audit_type)
    else:
        _d = AuditRecordsModel.objects()
    if name:
        _d = _d.filter(
            __raw__={'content': {'$regex': f'.*{name}'}}
        )
    _data = list(map(lambda x: convert_mongo_document_to_schema(x, AuditRecordsSchema, user=True,
                                                                revers_map=['applicant', 'auditor', 'component']), _d))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success",
                                 "data": _data[skip: skip+limit],
                                 "total": len(_data)})


@router.put('/components_tree/tree')
def get_tools_dir(skip: int = 0,
                  limit: int = 10,
                  query_sets: dict = {},
                  current_user: UserModel = Depends(deps.get_current_user)
                  ):
    page = skip*limit
    if query_sets.get('name'):
        name = query_sets.pop('name')

        tools_tree_model = ToolsTreeModel.objects(**query_sets).filter(
            __raw__={'name': {'$regex': f'.*{name}'}})
    else:
        tools_tree_model = ToolsTreeModel.objects(**query_sets)

    tools_tree = list(map(lambda x: convert_mongo_document_to_schema(x, ToolsTreeResponseSchema,user=True),
                              tools_tree_model))
    for _ in tools_tree:
        _['tool_count'] = XmlToolSourceModel.objects(category=_['name']).count()

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            "msg": "Success",
                            "data": tools_tree[page: page+limit],
                            "total": len(tools_tree)
                        }
                        )


@router.get('/components_tree/dir')
def get_tools_dir(current_user: UserModel = Depends(deps.get_current_user)):
    tools_ls = [{'name': _.name, 'parent': _.parent, 'level': _.level, 'id': _.id}for _ in ToolsTreeModel.objects]
    def generate_dir(source, parent):
        tree = []
        for item in source:
            if item["parent"] == parent:
                item["child"] = generate_dir(source, item["name"])
                tree.append(item)
        return tree
    tools_dir = generate_dir(tools_ls, 'root')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            "msg": "Success",
                            "data": tools_dir
                        }
                        )


@router.post('/components_tree/tree')
def post_tools_dir(dir_instance: ToolsTreeSchema,
                   current_user: UserModel = Depends(deps.get_current_user)):
    _id = str(uuid.uuid4())
    dir_instance.id = _id
    tool_dir = ToolsTreeModel(**dir_instance.dict(), user=current_user)
    tool_dir.save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            "msg": "Success"
                        }
                        )


@router.put('/components_tree/tree/{dir_name}')
def update_component_tree(dir_name: str,
                     update_set: dict,
                     current_user: UserModel = Depends(deps.get_current_user)
                     ):
    try:
        ToolsTreeModel.objects(name=dir_name).update_one(**update_set)
        XmlToolSourceModel.objects(category=dir_name).update(category=update_set['name'])
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.delete('/components_tree/tree/{tools_id}')
def delete_tools_dir(tools_id: str,
                     current_user: UserModel = Depends(deps.get_current_user)):
    try:
        ToolsTreeModel.objects(id=tools_id).delete()
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={
                                "msg": "Success"
                            }
                            )
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={
                                "msg": str(e)
                            })
