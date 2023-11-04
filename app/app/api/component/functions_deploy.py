# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:functions_deploy
@time:2022/09/09
"""
import os
import shutil
import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
    BackgroundTasks
)
from app.standalone.components.builder import StandaloneFunctionDeployer
from app.utils.middleware_util import get_redis_con
from fastapi.websockets import WebSocket
from fastapi.responses import JSONResponse
from app.api import deps
from app.core.config import settings
from app.core.gate import PublishTask
from app.models.mongo import UserModel
from app.models.mongo.tool_source import XmlToolSourceModel
from app.models.mongo.fair import FairMarketComponentsModel
from app.core.deploy_functions import FunctionDeployer
from app.utils.tool_util.xml_parser import ToolZipSource
from app.utils.file_util import chunked_copy, clean_after_fail_parse_tool_zip
from app.core.fair.market import FairMarketComponent
from app.utils.k8s_util.cluster import CloudCluster
from app.models.mongo.fair import FairMarketComponentsTreeModel, \
    MarketComponentsInstallTaskModel, VisualizationComponentModel
from app.schemas.fair import FairMarketComponentSchema, \
    FairMarketComponentsTreeSchema,\
    MarketComponentsInstallTaskSchema

from app.utils.common import convert_mongo_document_to_schema
router = APIRouter()


@router.post("/function/upload",
             summary="Operator compression package(zipFormat)Upload")
def package_upload(files: List[UploadFile],
                   current_user: UserModel = Depends(deps.get_current_user)):
    """
    Upload  (Format zip)
    """
    # The storage directory for the user，Plus the user, Used to distinguish
    USER_SPACE = current_user.id if current_user is not None else ""
    USER_ID = current_user.id if current_user is not None else ""
    storage_path = Path(settings.BASE_DIR, settings.TOOL_ZIP_PATH, USER_SPACE)
    package_storage_path = Path(settings.BASE_DIR, settings.TOOL_PATH, USER_SPACE, files[0].filename.replace('.zip', ''))
    zip_storage_path = Path(settings.BASE_DIR, settings.TOOL_ZIP_PATH, USER_SPACE, files[0].filename)
    print(storage_path)
    if not (storage_path.exists() and storage_path.is_dir()):
        storage_path.mkdir(parents=True)
    if package_storage_path.exists():
        shutil.rmtree(package_storage_path.absolute())
        print(f'already  tools package dir remove : {package_storage_path.absolute()}')
    if zip_storage_path.exists():
        os.remove(zip_storage_path.absolute())
        print(f'already  tools zip file remove : {zip_storage_path.absolute()}')
    print(f'uploading <{len(files)}> files: {[file.filename for file in files]}')
    tool_objs = XmlToolSourceModel.objects(xml_name=files[0].filename.replace('.zip', '.xml')).first()
    if tool_objs:
        print(f'already  tools: {tool_objs}')
        tool_objs.delete()
    for file in files:
        filename = file.filename
        logging.info(f"file: {filename}")
        # TODO: Whether you need to restrict the format of the archive?
        if not filename.endswith(".zip"):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid file format: {filename}"})
        # Store in a directory
        dest_path = Path(storage_path, filename)
        chunked_copy(file.file, dest_path)
        logging.info(f"uploaded: {filename}")
        # Start parsing
        try:
            extractResult = ToolZipSource(zip_name=filename,
                                          user_space=USER_SPACE,
                                          user_id=USER_ID).extract_xml_tool_source()
            # Check that parsing is normal.
            if extractResult.code != 0:
                # Delete extra files and folders
                try:
                    clean_after_fail_parse_tool_zip(zipfile_name=filename,
                                                    user_space=USER_SPACE)
                except Exception as e:
                    logging.warning(e)
                finally:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"code": extractResult.code,
                                                 "msg": extractResult.msg,
                                                 "data": extractResult.data})
            # Getting extract data
            xmlToolSource = extractResult.data
            # Deposit in db

            parseResult = xmlToolSource.save_to_db()

            if parseResult.code != 0:
                # Delete extra files and folders
                try:
                    clean_after_fail_parse_tool_zip(zipfile_name=filename,
                                                    user_space=USER_SPACE)
                except Exception as e:
                    logging.warning(e)
                finally:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"code": parseResult.code,
                                                 "msg": parseResult.msg,
                                                 "data": parseResult.data})
        except Exception as e:
            logging.warning(e)
            # Delete extra files and folders
            try:
                clean_after_fail_parse_tool_zip(zipfile_name=filename,
                                                user_space=USER_SPACE)
            except Exception as e:
                logging.warning(e)
            finally:
                JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                             content={"msg": f"file failed to parse: {filename}"})
    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "Success", "id": parseResult.data.id})


# @router.post("/deploy/{component_id}")
# def deploy_function(component_id: str,
#                     background_task: BackgroundTasks,
#                     current_user: UserModel = Depends(deps.get_current_user)):
#     fd = FunctionDeployer(component_id, current_user.id)
#     background_task.add_task(fd.create_temporary)
#     return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "Success", "id": component_id})
#

# @router.post("/standalone/deploy/{component_id}")
@router.post("/deploy/{component_id}")
async def deploy_function(component_id: str,
                    background_task: BackgroundTasks,
                    current_user: UserModel = Depends(deps.get_current_user)):
    # publisher = get_redis_con(1)
    # publisher.rpush(component_id, "start")
    # publisher.set(f"{component_id}-task", "start")
    # StandaloneFunctionDeployer(component_id, current_user.id).create_temporary()
    # publisher.set(f"{component_id}-task", "build")
    # publisher.set(f"{component_id}-task", "push")
    # publisher.set(f"{component_id}-task", "deploy")
    # publisher.close()
    fd = FunctionDeployer(component_id, current_user.id)
    background_task.add_task(fd.create_temporary)
    publisher = get_redis_con(1)
    publisher.rpush(component_id, "start")
    publisher.set(f"{component_id}-task", "start")
    publisher.close()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "Success", "id": component_id})

    # return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "Success", "id": component_id})


@router.websocket("/ws/{tool_id}")
async def websocket(websocket: WebSocket,
                    tool_id: str):
    publisher = PublishTask(tool_id, 1)
    _index = 0
    await websocket.accept()
    while 1:
        try:
            _status = None
            _data = None
            _msg = [_ for _ in publisher.publisher(start_index=_index)]
            _index += len(_msg)
            await websocket.send_json({"status": publisher.status, "data": [publisher.status]})
            await asyncio.sleep(1)
        except Exception as e:
            await websocket.send_json({"status": "FAILED", "data": [f"Build exception"]})
            break
    await websocket.close(code=1000)


@router.post('/market/install')
async def fair_market_components_list(
        component_id: str,
        background_task: BackgroundTasks,
        current_user: UserModel = Depends(deps.get_current_user)
):
    _component = FairMarketComponentsModel.objects(id=component_id).first()
    if _component is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Component does not exist"})
    background_task.add_task(FairMarketComponent(component_id, current_user.id).run)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Starting the installation",
                                 "data": None})


@router.get('/install/task')
async def get_component_install_task_list(skip: int = 0,
                                          limit: int = 10,
                                          name: str = None,
                                          state: str = None,
                                          source_type: str = None,
                                          current_user: UserModel = Depends(deps.get_current_user)):
    """
    Component installation list </br>
    :param skip: Paging parameters </br>
    :param limit: Paging parameters</br>
    :param name: Searching by name</br>
    :param state: State-based retrieval PULL Pull the middle,BUILD Under construction,DEPLOY In installation,SUCCESS Finished,FAILED failure</br>
    :param source_type: Retrieved by source type，NATIVE Upload，MARKET Through the market </br>
    :param current_user:
    :return:
    """
    _data = list()
    skip = skip * limit
    name_contains_ins = None
    if name:
        if source_type:
            if source_type == "NATIVE":
                name_contains_ins = XmlToolSourceModel.objects(name__contains=name)
            elif source_type == "MARKET":
                name_contains_ins = FairMarketComponentsModel.objects(name__contains=name)
            else:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": "Unsupported types"})
        else:
            name_contains_ins = list()
            for _ in XmlToolSourceModel.objects(name__contains=name):
                name_contains_ins.append(_)
            for _ in FairMarketComponentsModel.objects(name__contains=name):
                name_contains_ins.append(_)
            if not name_contains_ins:
                return JSONResponse(status_code=status.HTTP_200_OK,
                                    content={"data": list(),
                                             "total": 0,
                                             "msg": "Successful!"})

    query = {k: v for k, v in {"status": state, "source_type": source_type, "source__in": name_contains_ins}.items() if v is not None}
    for _ in MarketComponentsInstallTaskModel.objects(**query).order_by('-installed_at'):
        try:
            _d = convert_mongo_document_to_schema(_,
                                                  MarketComponentsInstallTaskSchema,
                                                  revers_map=['installed_user', 'source'])
            _d['source_id'] = _.source.id
            _data.append(_d)
        except:
            pass
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _data[skip: skip + limit],
                                 "total": len(_data),
                                 "msg": "Successful!"})


@router.post('/install/task')
async def create_component_install_task(
                                        current_user: UserModel = Depends(deps.get_current_user)):
    # from app.utils.common import generate_uuid
    # _a = FairMarketComponentsModel.objects(id="f6a70ff8ed1846b0ba3fa66954").first()
    # _data = [{'source': "79696902-0a49-44ca-9308-e3002a810251", "installed_user": "0993bc4a65fa4d638dcdcf44030f7194",  "reinstall": False, "reinstall_nums": 0, "status": "PULL", "source_type": "NATIVE"},
    # {'source': "07466036-6a4b-41b7-bfb9-9c7a30682ec7", "installed_user": "0993bc4a65fa4d638dcdcf44030f7194",  "reinstall": False, "reinstall_nums": 0, "status": "BUILD", "source_type": "NATIVE"},
    # {'source': "81acc797-0cfe-47b7-98d0-34050d135a59", "installed_user": "0993bc4a65fa4d638dcdcf44030f7194", "reinstall": False, "reinstall_nums": 0, "status": "PUSH", "source_type": "NATIVE"},
    # {'source': "eeb73139-b6d2-4f97-b512-426a161b709c", "installed_user": "0993bc4a65fa4d638dcdcf44030f7194",  "reinstall": False, "reinstall_nums": 0, "status": "DEPLOY", "source_type": "NATIVE"},
    # {'source': "9e950663-0512-495a-a745-1c0939bf17c2", "installed_user": "0993bc4a65fa4d638dcdcf44030f7194", "reinstall": False, "reinstall_nums": 0, "status": "SUCCESS", "source_type": "NATIVE"}]
    # for _ in _data:
    #     _a = XmlToolSourceModel.objects(id=_['source']).first()
    #     MarketComponentsInstallTaskModel(**{'id': generate_uuid(), 'source': _a, "installed_user": current_user,  "reinstall": False, "reinstall_nums": 0, "status": _['status'], "source_type": "NATIVE"}).save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful"})


@router.get('/market/components')
async def fair_market_components_list(
        component_id: str = None,
        component_name: str = None,
        author: str = None,
        category: str = None,
        order_by: str = None,
        page: int = 0,
        limit: int = 10,
        suffix: str = None,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Access the Fast man market
    """
    skip = page * limit
    FairMarketComponent().get_market_component()
    if suffix is None:
        _query = {k: v for k, v in {"id": component_id, 'name__contains': component_name, 'authorName': author, "category": category
                                    }.items() if
                  v is not None}
        if order_by is None:
            order_by = "-CreateAt"
        else:
            order_by = f"-{order_by}"
        _d = FairMarketComponentsModel.objects(**_query).order_by(order_by)
        _data = list()
        for i in map(lambda x: convert_mongo_document_to_schema(x, FairMarketComponentSchema),
                         _d):
            # print(i['parameters'])
            try:
                i['parameters'] = {_p['key']: _p['value'] for _p in  i['parameters']}
            except KeyError:
                pass
            _data.append(i)
        # _data = [ for i in map(lambda x: convert_mongo_document_to_schema(x, FairMarketComponentSchema),
        #                  _d)]
    else:
        print([_i.id for _i in VisualizationComponentModel.objects(support__in=suffix)])
    content = dict()
    content['data'] = dict()
    content['data']['list'] = _data[skip: skip+limit]
    content['data']['total'] = len(_data)
    content['message'] = "Successful!"
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=content)


@router.get('/market/components/tree')
async def fair_market_component_tree(current_user: UserModel = Depends(deps.get_current_user)):
    # _d = FairMarketComponentsTreeModel.objects
    'category'
    category = dict()
    _d = FairMarketComponentsModel.objects
    for i in _d:
        if category.get(i.category) is None:
            category[i.category] = 0
        category[i.category] += 1
    _data = [{"category": k, "counts": v} for k, v in category.items()]
    # _data = list(map(lambda x: convert_mongo_document_to_schema(x, FairMarketComponentsTreeSchema),
    #                  _d))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _data, "message": "Successful!"})

