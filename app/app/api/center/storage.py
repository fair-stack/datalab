# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:storage
@time:2022/09/29
"""
import re
import os
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    status,
    Request,
    Form,
    File,
    UploadFile
)
import datetime
from typing import Optional
from fastapi.responses import JSONResponse
from app.api import deps
from app.models.mongo import UserModel, StorageResourceAllocatedModel
from app.models.mongo.dataset import DataFileSystem
from app.schemas.dataset import DatasetV2Schema
from app.utils.common import convert_mongo_document_to_schema
from app.utils.common import generate_uuid
from app.utils.resource_util import get_cache_cumulative_num
from app.utils.file_util import generate_datasets_model, del_datasets, share_util
from app.models.mongo.public_data import PublicDataFileModel, PublicDatasetModel
from app.utils.middleware_util import get_s3_client
from app.utils.file_util import stream_to_b64_stream
from app.utils.resource_util import cache_cumulative_sum, cut_user_storage_size
from app.schemas.public_data import PublicDataFileSchema, PublicDatasetSchema
from app.core.config import settings
from app.service.manager.storage import StorageManager
from app.service.manager.datasets import DatasetsManager
# from app.service.response import DataLabResponse
router = APIRouter()


@router.get('/')
async def my_data_list(
        request: Request,
        skip: int = 0,
        limit: int = 10,
        name: str = None,
        dataset_id: str = None,
        data_path: str = None,
        current_user: UserModel = Depends(deps.get_current_user)
):

    skip = skip * limit
    _query = dict()
    # sum = await get_cache_cumulative_num(current_user.id, request.app.state.use_storage_cumulative)
    sum = DataFileSystem.objects(user=current_user, is_dir=False, deleted=False, public=None).sum('data_size')
    _total_size = StorageResourceAllocatedModel.objects(allocated_user=current_user.id).first().allocated_storage_size
    if dataset_id is not None:
        # Priority processing dataset_id Does it exist
        _dfs = DataFileSystem.objects(id=dataset_id, deleted=False).first()
        if _dfs is None:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"msg": "Show all datasets",
                                         "data": [],
                                         "size": sum,
                                         'total_size': _total_size,
                                         'total': 0})
        if _dfs.data_type == "TaskData":
            _data = list()
            if name:
                task_data_list = DataFileSystem.objects(user=current_user.id,
                                       deps=_dfs.deps+1,
                                       deleted__in=[False, 0],
                                       task_id= _dfs.task_id,
                                       lab_id=_dfs.lab_id,
                                       name__contains=name)
            else:
                task_data_list = DataFileSystem.objects(user=current_user.id,
                                                        deps=_dfs.deps + 1,
                                                        deleted__in=[False, 0],
                                                        task_id=_dfs.task_id,
                                                        lab_id=_dfs.lab_id
                                                    )
            for _t in task_data_list:
                _d = convert_mongo_document_to_schema(_t, DatasetV2Schema, user=True, revers_map=['user'])
                _d['from_source'] = "COMPUTING" if _d['data_type'] == "TaskData" else "UPLOAD"
                _data.append(_d)

        else:
            _data = list()
            root_path = Path(data_path).resolve()
            if not root_path.exists():
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                    content={"msg": f"data_path not exists: {root_path}"})
            elif not root_path.is_dir():
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                    content={"msg": f"data_path is not dir: {root_path}"})
            else:
                path_list = list(root_path.iterdir())
                for path in path_list:
                    if name is not None and name not in path.name:
                        continue
                    sub_dataFileSystem = DataFileSystem.objects(data_path=path.as_posix()).first()
                    if sub_dataFileSystem is None:
                        continue
                    _d = convert_mongo_document_to_schema(sub_dataFileSystem, DatasetV2Schema, user=True,
                                                          revers_map=['user'])
                    _d['from_source'] = "COMPUTING" if _d['data_type'] == "TaskData" else "UPLOAD"
                    _data.append(_d)
        _total = len(_data)
        _data = _data[skip: skip + limit]

    else:
        # Not a solicitation
        if name:
            _dfs = DataFileSystem.objects(user=current_user.id, deleted=False,
                                          name__contains=name).order_by("-created_at")
        else:
            _dfs = DataFileSystem.objects(user=current_user.id, deps=0, deleted=False).order_by("-created_at")
        _data = list()
        _total = _dfs.count()
        if _dfs:
            for _obj in _dfs.skip(skip).limit(limit):
                _d = convert_mongo_document_to_schema(_obj, DatasetV2Schema, user=True,revers_map=['user'])
                _d['from_source'] = "COMPUTING" if _d['data_type'] == "TaskData" else "UPLOAD"
                _data.append(_d)

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Show all datasets",
                                 "data": _data,
                                 "size": sum,
                                 'total_size': _total_size,
                                 'total': _total})


@router.put('/rename/{data_id}', summary="Changing data names")
async def rename_datasets(data_id: str, name: str, current_user: UserModel = Depends(deps.get_current_user)):
    _double_quotation = '"'
    _single_quotation = "'"
    character = re.findall(f'[/${_double_quotation}{_single_quotation}*<>?\\/|：:]', name)
    if character:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"An invalid character exists in the name< {' '.join(character)} >"})
    if name[0] == " " or name[0] == ".":
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "No Spaces or.As a head start"})
    _model = DataFileSystem.objects(id=data_id, deleted=False).first()
    if _model is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": "Data does not exist"})
    _model.name = name
    _model.updated_at = datetime.datetime.utcnow()
    try:
        _model.save()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": "Limited modification"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "Successful!"})


@router.get('/share', summary='I share the data retrieval')
async def my_share(
            request: Request,
            skip: int = 0,
            limit: int = 10,
            user_name: str = None,
            current_user: UserModel = Depends(deps.get_current_user)
    ):
        skip = skip * limit
        if user_name:
            users = [u.id for u in UserModel.objects(name__contains=user_name)]
            _dfs = DataFileSystem.objects(from_user=current_user, user__in=users, deps=0)
        else:
            _dfs = DataFileSystem.objects(from_user=current_user,deps=0)
        sum = await get_cache_cumulative_num(current_user.id, request.app.state.use_storage_cumulative)
        _total_size = StorageResourceAllocatedModel.objects(
            allocated_user=current_user.id).first().allocated_storage_size
        if _dfs:
            _data = list(map(lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema, user=True,
                                                                        revers_map=['user']), _dfs))
        else:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"msg": "Show all datasets",
                                         "data": [],
                                         "size": sum,
                                         'total_size': _total_size,
                                         'total': 0})
        _total_size = StorageResourceAllocatedModel.objects(
            allocated_user=current_user.id).first().allocated_storage_size
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Show all datasets",
                                     "data": _data[skip: skip + limit],
                                     "size": sum,
                                     'total_size': _total_size,
                                     'total': len(_data)})


@router.get('/from_share', summary='Data retrieval from shared')
async def my_share(
            request: Request,
            skip: int = 0,
            limit: int = 10,
            user_name: str = None,
            current_user: UserModel = Depends(deps.get_current_user)
    ):
        skip = skip * limit
        if user_name:
            users = [u.id for u in UserModel.objects(name__contains=user_name)]
            _dfs = DataFileSystem.objects(from_user=current_user, from_user__in=users,deps=0)
        else:
            users = [u.id for u in UserModel.objects()]
            _dfs = DataFileSystem.objects(user=current_user.id, from_user__in=users,deps=0)
        sum = await get_cache_cumulative_num(current_user.id, request.app.state.use_storage_cumulative)
        user_size = StorageResourceAllocatedModel.objects(
            allocated_user=current_user.id).first()
        # if user_size is None:
        #     return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
        #                     content={"msg": "No storage resources available"}
        #                              )
        _total_size = user_size.allocated_storage_size
        if _dfs:
            _data = list(map(lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema, user=True,
                                                                        revers_map=['user', 'from_user']), _dfs))
        else:
            return JSONResponse(status_code=status.HTTP_200_OK,
                                content={"msg": "Show all datasets",
                                         "data": [],
                                         "size": sum,
                                         'total_size': _total_size,
                                         'total': 0})

        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Show all datasets",
                                     "data": _data[skip: skip + limit],
                                     "size": sum,
                                     'total_size': _total_size,
                                     'total': len(_data)})


@router.post('/share', summary="Share my data with other users")
async def my_data_share(
        request: Request,
        datasets_id: str,
        share_user_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):

    _d = DataFileSystem.objects(id=datasets_id).first()
    if _d is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Resource does not exist！"})
    if DataFileSystem.objects(from_source=datasets_id, user=share_user_id).first():
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "The data has been shared"})
    share_util(_d, share_user_id, current_user)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"})


@router.delete('/share', summary="Unshare")
async def undo_data_share(
        request: Request,
        datasets_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):

    _d = DataFileSystem.objects(id=datasets_id).first()
    if _d is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Resource does not exist！"})
    ids = generate_datasets_model(_d.id, _d.user.id)
    _dfs = DataFileSystem.objects(id__in=ids)
    for i in _dfs:
        i.delete()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"})


@router.get('/public', summary="Access to open data")
async def get_public_data(name: str = None,
                          page: int = 0,
                          limit: int = 10,
                          current_user: UserModel = Depends(deps.get_current_user)):
    if not DatasetsManager.access():
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": [],
                                     "total": 0,
                                     "msg": "Successful!"})
    client = get_s3_client()
    if name:
        _dfs = PublicDatasetModel.objects(name__contains=name, access="PUBLIC")
    else:
        _dfs = PublicDatasetModel.objects(access="PUBLIC")
    data = list()
    if not _dfs:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": list(),
                                     "total": 0,
                                     "msg": "Successful!"})
    for _ in _dfs:
        _d = convert_mongo_document_to_schema(_, PublicDatasetSchema, user=True)
        _d['icon'] = stream_to_b64_stream(client.get_object(_.id, _.icon).read())
        inner_files = PublicDataFileModel.objects(datasets=_.id).order_by("created_at").first()
        _d['create_at'] = inner_files.created_at.strftime('%Y/%m/%d %H:%M:%S') if inner_files else None
        data.append(_d)
    skip = page * limit
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": data[skip: skip+limit],
                                 "total": len(data),
                                 "msg": "Successful!"})


@router.get('/public/data', summary="Access to open data")
async def get_public_file(
        dataset_id: str,
        name: str = None,
        file_extension: str = None,
        page: int = 0,
        limit: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)):
    query_map = {k: v for k, v in {"name__contains": name, "file_extension": file_extension}.items() if v is not None}
    query_map['datasets'] = dataset_id
    _dfs = PublicDataFileModel.objects(**query_map)
    data = list()
    for _ in _dfs:
        _d = convert_mongo_document_to_schema(_, PublicDataFileSchema)
        data.append(_d)
    skip = page * limit
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": data[skip: skip+limit],
                                 "total": len(data),
                                 "msg": "Successful!"})


@router.delete('/', summary="Delete/Delete")
async def delete_datasets(request: Request,
                          datasets_id: list,
                          current_user: UserModel = Depends(deps.get_current_user)):
    try:
        await del_datasets(datasets_id, current_user, request.app.state.use_storage_cumulative)
    except Exception as e:
        print(f"Personal Center-DeleteAPI：{e}:{datasets_id}, {current_user.name}, {current_user.id}")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Delete！"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!"})


@router.get('/datasets')
async def get_all_datasets(current_user: UserModel = Depends(deps.get_current_user)):
    if not DatasetsManager.access():
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": [],
                                     "total": 0,
                                     "msg": "Successful!"})
    if current_user.role == "ADMIN":
        _admin = True
    else:
        _admin = False
    _datasets = DatasetsManager.datasets(_admin)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _datasets,
                                 "total": len(_datasets),
                                 "msg": "Successful!"})


@router.get('/datasets/{datasets_id}', summary="Get the data file under the dataset")
async def get_datasets_file(
        dataset_id: str,
        name: str = None,
        file_extension: str = None,
        page: int = 0,
        limit: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)):
    query_map = {k: v for k,v in {"name__contains": name, "file_extension": file_extension}.items() if v is not None}
    query_map['datasets'] = dataset_id
    _dfs = PublicDataFileModel.objects(**query_map).order_by("-updated_at")
    data = list()
    for _ in _dfs:
        _d = convert_mongo_document_to_schema(_, PublicDataFileSchema)
        data.append(_d)
    skip = page * limit
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": data[skip: skip+limit],
                                 "total": len(data),
                                 "msg": "Successful!"})


@router.post("/upload/file")
async def upload_big_file(request: Request,
                          file: UploadFile = File(...),
                          chunk_number: str = Form(...),  # Current shard
                          identifier: str = Form(...),  # Unique identification
                          total_size: int = Form(...),  # Current total file size
                          total_chunks: int = Form(...),  # Total number of slices in the current file
                          relative_path: str = Form(...),  # Absolute path
                          current_chunk_size: int = Form(...),  # Total upload size
                          current_user: UserModel = Depends(deps.get_current_user)
                          ):  # Shard upload file [with unique identifier+Shard sequence number  as the filename
    user_used = await get_cache_cumulative_num(current_user.id, request.app.state.use_storage_cumulative)
    _total_size = StorageResourceAllocatedModel.objects(allocated_user=current_user.id).first().allocated_storage_size
    if _total_size-user_used < total_size:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Insufficient storage space"})
    if len(chunk_number) == 0 or len(identifier) == 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Missing identifier"})
    filename = f'{relative_path}{identifier}{chunk_number}'  # ShardingUnique identification
    contents = await file.read()  # Read a file asynchronously
    storage_path = Path(settings.BASE_DIR, settings.DATA_PATH, current_user.id)
    _path = Path(filename)
    if _path.parent != "." and _path.parent != "/":
        mks_name = f"{storage_path}/uploads/{_path.parent}"
        try:
            os.makedirs(mks_name)
        except FileExistsError:
            pass
    with open(f"{storage_path}/uploads/{filename}", "wb") as f:
        f.write(contents)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": f"Received{relative_path}Sharding{chunk_number}"})


@router.post("/upload/merge_file")
async def merge_file(request: Request,
                     identifier: str = Form(...),
                     file_name: str = Form(...),
                     chunk_star: int = Form(...),  # Unique identification
                     current_user: UserModel = Depends(deps.get_current_user)):
    if len(file_name) == 0 or len(identifier) == 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Missing identifier"})
    storage_path = Path(settings.BASE_DIR, settings.DATA_PATH, current_user.id)
    _mode_base = f"{file_name}{identifier}*"
    _mode_path = f"{storage_path}/uploads"
    if len(file_name.split('/')) > 1:
        _mode_base = f"{file_name.rsplit('/', maxsplit=1)[-1]}{identifier}*"
        _mode_path = f"{storage_path}/uploads/{file_name.rsplit('/', maxsplit=1)[0]}"
    _path = Path(_mode_path)
    merge_task = dict()
    for i in _path.rglob(_mode_base):
        _relative_path, _suffix = i.__fspath__().rsplit(identifier, maxsplit=1)
        if merge_task.get(_relative_path) is None:
            merge_task[_relative_path] = list()
        merge_task[_relative_path].append(i.__fspath__())
    for k, v in merge_task.items():
        v.sort()
        with open(k, 'wb') as f:
            for _file_name in v:
                with open(_file_name, 'rb') as reader:
                    f.write(reader.read())
                os.remove(_file_name)
    absolute_path = f"{storage_path}/uploads/{file_name}"
    # StorageManager.from_dir(absolute_path, current_user)
    # request.app.state.use_storage_cumulative
    _model = StorageManager.save_file(absolute_path, file_name, current_user)
    try:
        await cache_cumulative_sum(current_user.id, _model.data_size, _model.data_path,
                                   request.app.state.use_storage_cumulative)
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Insufficient user resource margin！"})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"file": file_name, "msg": "Successful!"})


@router.get('/geoserver/datasets')
async def search_geoserver_datasets(current_user: UserModel = Depends(deps.get_current_user)):
    dfs = DataFileSystem.objects(file_extension__in=["shp", "shape", "tif", "tiff"])
    data = list(
        map(lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema, user=True, revers_map=['user']), dfs
            ))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": data})

#
# @router.get('/digital/datasets/asset')
# async def digital_assets_datasets(
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#
#     DataFileSystem.objects(user=current_user, is_dir=False, deleted=False)

