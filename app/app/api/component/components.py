# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:components
@time:2022/08/23
"""
import pickle
import asyncio
import requests
from minio.deleteobjects import DeleteObject
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocket
from fastapi import (
    APIRouter,
    status,
    Depends,
    Request,
    Form
)
from minio import S3Error
import json
import pandas
from minio.error import S3Error
from app.api import deps
from app.core.gate import PublishTask
from app.core.gate import runtime_exec, post_function, FunctionEvent
from app.utils.common import convert_mongo_document_to_schema
from app.utils.middleware_util import get_s3_client, s32dir_tree
from app.service.manager.event import EventManager
from app.models.mongo import (
    UserModel,
    DataFileSystem,
    XmlToolSourceModel,
    ComponentInstance,
    VisualizationComponentModel,

)
from app.models.mongo.fair import FairMarketComponentsModel
from app.schemas.component import ComponentInstanceSchema
from app.storage.object_storage import object_storage_stream
from app.storage.file_system import file_storage_stream
from app.schemas.dataset import DatasetV2Schema
from app.schemas.visualization import VisualizationDataInCrate, VisualizationComponentsResponse
from app.core.serialize.ptype import frontend_map
from app.service.manager.visualization import VisualizationManager
from app.service.manager.task import ComputeTaskManager
from app.core.config import settings
router = APIRouter()


@router.delete('/component/{function_name}')
def delete_component(component_id: str,
                     current_user: UserModel = Depends(deps.get_current_user)):
    try:
        XmlToolSourceModel.objects(id=component_id).first().delete()
        ComponentInstance.objects(base_id=component_id).first().delete()
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Component removal failed：{e}"})


@router.post('/component/{function_name}')
def component_start(function_name: str = 'plasmabubble', data: dict = {}):
    try:
        if function_name == 'plasmabubble':
            data['data_dir'] = 'Test_plasma_bubble'
            data['gateway_task_data'] = {}
            data['gateway_task_data']['load_data'] = None
            data['gateway_task_data']['upload_data'] = [
                {
                    "bucket": data['task_id'],
                    "object_name": "noepb",
                },
                {
                    "bucket": data['task_id'],
                    "object_name": "plasmabubble",
                }
            ]
            data["datalab_launch"] = {"package_dir": "/home/app/function",
                           "file_name": "/home/app/function/handler.py",
                           "function_name": "handle"}

        task_id = post_function(function_name, data)
        return task_id
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": str(e)})


@router.get('/result/{task_id}')
def component_start(task_id: str,
                    current_user: UserModel = Depends(deps.get_current_user)):
    """
    Result export
    """
    try:
        print(f"Get task result {task_id}")
        publisher = PublishTask(task_id)
        _status = None
        _data = None
        if publisher.status == "Success":
            _status = "Success"
            content = {"status": _status, "data": [_ for _ in publisher.publisher()]}
        elif publisher.status == 'Error':
            _status = "Failed"
            for _ in publisher.publisher():
                content = {"status": _status, "data": _}

        elif publisher.status == 'Pending':
            _status = "Pending"
            content = {"status": _status, "data": publisher.pending()}
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=content)
    except Exception as e:
        print(f"Get task result failed {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to task for id: {task_id}"})


@router.websocket("/ws/{lab_task_id}")
async def websocket(websocket: WebSocket, lab_task_id: str):
    print(lab_task_id)
    publisher = PublishTask(lab_task_id)
    _index = 0
    await websocket.accept()
    while 1:
        _status = None
        _data = None
        _msg = [_ for _ in publisher.publisher(start_index=_index)]
        _index += len(_msg)
        _status = "Failed" if publisher.status == "Error" else publisher.status
        await websocket.send_json({"status": _status, "data": _msg})
        await asyncio.sleep(1)
    await websocket.close(1000)


@router.get('/visualization/{data_id}',
            response_model=VisualizationComponentsResponse)
async def visualization(data_id: str,
                        current_user: UserModel = Depends(deps.get_current_user)):
    VisualizationManager.map(data_id)
    try:
        return VisualizationManager.map(data_id)
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": None})


@router.delete('/visualization/{component_id}')
async def delete_visualization_component(
        component_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    _component_entity = FairMarketComponentsModel.objects(id=component_id).first()
    if _component_entity is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Component does not exist"})
    import shutil
    import os
    shutil.rmtree(os.path.join(settings.MARKET_FRONT_COMPONENT_DOWNLOAD_DIR, component_id))
    VisualizationComponentModel.objects(source__in=[_component_entity]).delete()
    _component_entity.delete()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Delete successfully！"})


@router.post('/visualization_data')
async def create_visualization_response(data: VisualizationDataInCrate,
                                        current_user: UserModel = Depends(deps.get_current_user)):
    try:
        # return VisualizationManager.create_from_requests(data).create_data(current_user)
        return {
            "code": 0,
            "message": True,
            "data": {"background": "#fff",
                     "fileUrl": ["http:/127.0.0.1/market_component/static/03a945873b4b4115bf5f3d27ce.png"]
                     },
            "count": None
        }
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"An exception occurred to build visualization data: {e}"})


@router.post('/custom/link')
async def update_market_component_custom(component_id: str,
                                         params: list,
                                         current_user: UserModel = Depends(deps.get_current_user)
                                         ):
    _component = FairMarketComponentsModel.objects(id=component_id).first()
    if _component is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Component does not exist"})

    # try:
        # request = requests.get(link)
        # _response_code = request.status_code
    _component.parameters = params
    _model = VisualizationComponentModel.objects(source=_component).first()
    _model.response_schema = params
        # if i.get("key") == "custom":
        #     i['value'] = params
    try:
        _component.save()
        _model.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                        content={"msg": "Parameter exception"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})
    # except requests.exceptions.HTTPError as e:
    #     return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
    #                         content={"msg": "Address not available"})


@router.post('/vis/{function_name}')
def vis(function_name: str = 'csvis',
        data: dict = {},
        current_user: UserModel = Depends(deps.get_current_user)
        ):
    """
    :param function_name: faas visualization function service <br>
    :param data: <br>       example {"bucket": "test", "object_name": "c/c/c/res.csv"} <br>
    :return: {"data": [], "msg":"", "code"}
    """
    # if function_name == "samvis" or function_name == "fastqvis" or function_name == "fqvis":
    #     function_name = "txtvis"

    try:
        file_instance = DataFileSystem.objects(id=data['id']).first()
        if file_instance is not None:
            # Whether the judgment comes from sharing data
            if file_instance.from_source is not None and file_instance.from_source != '':
                source_data = file_instance
            else:
                source_data = DataFileSystem.objects(id=file_instance.from_source).first()
            if source_data.data_type == "myData":
                data['bucket'] = source_data.user.id
                data['object_name'] = source_data.data_path
                client = get_s3_client()
                if not client.bucket_exists(data['bucket']):
                    client.make_bucket(data['bucket'])
                try:
                    client.stat_object(data['bucket'], data['object_name'])
                except S3Error:
                    client.fput_object(data['bucket'], data['object_name'], data['object_name'])
            else:
                data['bucket'] = source_data.lab_id
                data['object_name'] = f"{source_data.task_id}/{source_data.data_path}"
        data.pop('id')
        client = get_s3_client()
        if function_name == 'csvvis':
            _data = pandas.read_csv(client.get_object(data['bucket'], data['object_name'])).to_dict('records')
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"content": _data})
        if function_name == "txtvis":
            _data = client.get_object(data['bucket'], data['object_name']).read().decode()
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"content": _data})
        if function_name in ["pngvis", "jpgvis", "jpegvis", 'tifvis', 'tiffvis', 'rawvis', 'bmpvis', 'gifvis']:
            _name = f'/market_component/static/{file_instance.id}.{file_instance.name.rsplit(".")[-1]}'
            with open(f'/home/datalab/dist/market_component/static/{file_instance.id}.{file_instance.name.rsplit(".")[-1]}', 'wb') as f:
                f.write(client.get_object(data['bucket'], data['object_name']).read())
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"imgList": [_name]}
                                )
        if function_name in ["samvis", "bamvis", "fastqvis", "fastavis", "fqvis", "favis"]:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={
                                    "genome": "hg38",
                                    "locus": "chr8:127,736,588-127,739,371",
                                    "tracks": [
                                        {
                                            "name": "HG00103",
                                            "url": "https://s3.amazonaws.com/1000genomes/data/HG00103/alignment/HG00103.alt_bwamem_GRCh38DH.20150718.GBR.low_coverage.cram",
                                            "indexURL": "https://s3.amazonaws.com/1000genomes/data/HG00103/alignment/HG00103.alt_bwamem_GRCh38DH.20150718.GBR.low_coverage.cram.crai",
                                            "format": "cram"
                                        }]
                                    }
                                )
        # vis_resp = runtime_exec(function_name.lower(), method='POST', serialization=True, data=data)
        # return vis_resp
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": str(e)})


@router.post('/structure')
async def structure_view(lab_id: str,
                         task_id: str = None,
                         current_user: UserModel = Depends(deps.get_current_user)):
    client = get_s3_client()
    if task_id:
        try:
            _io = client.get_object(lab_id, task_id + '/' + "labVenvData.pkl")
            try:
                _object = pickle.load(_io)
            except Exception as e:
                _object = ""
            # Can beJsonTransfer format validation, coercionstr __str__
            _structure = frontend_map(_object, f"{lab_id}_{task_id}")
        except S3Error:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"msg": "The data has been released！"})

    else:
        _structure = list()
        try:
            for _ in client.list_objects(lab_id):
                try:
                    _io = client.get_object(lab_id, _.object_name + "labVenvData.pkl")
                except S3Error:
                    pass
                try:
                    _object = pickle.load(_io)
                except Exception as e:
                    # Can be
                    print(f"Serialization exception {e}: {lab_id}/{_.object_name}")
                    _object = None
                _structure.append(
                    frontend_map(_object, f"{lab_id}_{_.object_name.replace('/', '')}")
                )
        except S3Error:
            pass
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": _structure,
                                     "msg": "Successful!"}
                            )
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _structure,
                                 "msg": "Successful!"}
                        )

    # data = await request.app.state.objects_storage.hgetall(f"{lab_id}-{task_id}")
    # _structure_data = dict()
    # # The data entity is not shown yet - Can be
    # for k, v in data.items():
    #     new_key = k.decode()
    #     if new_key == 'data':
    #         v = pickle.loads(v)
    #     else:
    #         v = v.decode()
    #     _structure_data[new_key] = v


@router.get('/structure')
async def structure_schema(structure_id: str,
                           current_user: UserModel = Depends(deps.get_current_user)):
    """
    Returns a data structure description of a variable
    """
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": ""})


@router.delete('/datasets/{lab_id}')
def delete_dataset(lab_id: str,
                   task_id: str,
                   current_user: UserModel = Depends(deps.get_current_user)):
    try:
        client = get_s3_client()
        object_delete_list = [DeleteObject(_.object_name) for _ in
                              client.list_objects(lab_id, prefix=task_id,
                                                  recursive=True)]
        remove_ls = client.remove_objects(lab_id, object_delete_list)
        for _ in remove_ls:
            remove_obj = _
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'data': f"Remove task data error! {e}",
                     'msg': f'{e}'}
        )

    else:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'data': "Remove task data",
                     'msg': 'Successful'}
        )


@router.get('/resource/{task_id}')
async def get_runtime_resource_used(request: Request,
                                    task_id: str,
                                    current_user: UserModel = Depends(deps.get_current_user)):
    key = f"{task_id}-resource"
    try:
        resource_info = await request.app.state.task_publisher.get(key)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": json.loads(resource_info),
                                     "msg": "Successful"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.get('/datasets/{lab_id}')
def components_dataset(lab_id: str,
                       task_id: str = None,
                       name: str = None,
                       file_extension: str = None,
                       deps: int = 0,
                       current_user: UserModel = Depends(deps.get_current_user)
                       ):
    """
    Obtaining experimental data
    :param lab_id: Experimentid
    :param task_id: Operator executionid
    :param name: Fuzzy query name
    :param file_extension: File Type Classification
    :param skip: Paging parameters，Start bit
    :param limit: Paging parameters，Step size
    :param deps: depth
    :return:
    """
    if name is not None and name != "":
        name = name + '/'
    query_ = {k: v for k, v in {"lab_id": lab_id, "task_id": task_id, "name__contains": name, "file_extension": file_extension}.items() if k is not None and k !=''}

    if deps > 0 and name is None:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": "depth"})

    dataset_files = list()
    query_ = {k: v for k, v in query_.items() if v is not None}
    _dfs = DataFileSystem.objects(**query_, deps=deps)
    dataset_files.extend(
        map(
            lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema, user=True, revers_map=['user']),
            _dfs
        )
    )
    parent = None
    if dataset_files:
        parent = dataset_files[0]['parent']
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            'data': dataset_files,
                            'msg': 'Successful',
                            'parent': parent
                        }
                        )
    # datasets_list = s32dir_tree(lab_id, task_id)
    # if task_id is None:
    #     new_list = list()
    #     for _ in datasets_list:
    #         new_list.extend(s32dir_tree(lab_id, _['data_path']))
    #     datasets_list = new_list
    # return JSONResponse(status_code=status.HTTP_200_OK,
    #                     content={'data': datasets_list,
    #                              'msg': 'Successful'})


@router.get("/iterdir/{lab_id}", summary="Loop through the data folder")
def iterdir_task_dataset(lab_id: str,
                         dir_path: str,
                         current_user: UserModel = Depends(deps.get_current_user)
                         ):
    _d = s32dir_tree(lab_id, dir_path)
    if dir_path.endswith('/'):
        dir_path = dir_path[: -1]
    parent_dir = dir_path.rsplit('/',maxsplit=1)[0]+'/'
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={'data': _d,
                                 'msg': 'Successful',
                                 'parent_dir': parent_dir })


@router.get('/download')
async def download_lab_data(flag: str = None,
                            object_name: str = None,
                            current_user: UserModel = Depends(deps.get_current_user)):
    """
    Data download interface，flag Distinction Object Storage System/File storage system，Folders are compressed by default tozip <br>
    :param flag:  Distinction，My data is for temporary usemyDataMarking,ExperimentExperimentID <br>
    :param object_name: The path to the file to download/Object name <br>
    :return: StreamingResponse/The file does not exist404 <br>
    """
    if flag == "myData":
        objs = DataFileSystem.objects(user=current_user.id, data_path=object_name).order_by('-updated_at').first()
        if objs is None:
            file_name = None
        else:
            file_name = objs.name
        data_path = object_name
        result = await file_storage_stream(data_path, file_name=file_name)
    else:
        result = await object_storage_stream(flag, object_name)
    return result


@router.get('/function')
def get_all_components_isinstance(current_user: UserModel = Depends(deps.get_current_user)):
    component_list = list(map(lambda x: convert_mongo_document_to_schema(x, ComponentInstanceSchema),
                              ComponentInstance.objects))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": 'Success', "data": component_list})


@router.post('/test/{function_name}')
async def component_start(
        request: Request,
        function_name: str,
        data: dict = {},
        current_user: UserModel = Depends(deps.get_current_user)
):
    # FunctionEvent(current_user.id, function_name, **data).reaction("task")
    em = EventManager(function_name, data, current_user)
    _result = await em.trigger(request.app.state.task_publisher)
    if _result.get("code") != 200:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content=_result.get("content"))
    return JSONResponse(status_code=status.HTTP_200_OK, content=_result.get("content"))


@router.post('/callback/{task_id}')
async def task_callback_signal(request: Request, task_id: str):
    await ComputeTaskManager.success(task_id, request.app.state.task_publisher)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})
