# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:digital_asset
@time:2023/06/07
"""
import os
from pathlib import Path
from typing import Optional
from app.crud import crud_da
from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    Form,
    File,
    UploadFile,
)
from app.api import deps
from app.models.mongo import (
    DataFileSystem,
    UserModel,
    ExperimentModel,
    StorageResourceAllocatedModel
)
from fastapi.responses import StreamingResponse
from app.service.response import DataLabResponse
from app.service.manager.lake import DataLakeManager
from app.utils.common import generate_uuid, convert_mongo_document_to_schema
from app.models.mongo.digital_asset import ExperimentsDigitalAssetsModel
from app.models.mongo.digital import MultilingualGenericsModel
from app.models.mongo.digital import FileDigital
from app.schemas.digital_asset import ExperimentsDigitalAssetsSchema
from app.core.config import settings
router = APIRouter()


#  TODO  Multiple meanings only according to each full amountIDprocessing
@router.post('/experiments/asset', summary="Create a collection of experimental data assets")
async def create_experiments_asset_set(
        experiments_id: str,
        data_id: list[dict],
        current_user: UserModel = Depends(deps.get_current_user)
):
    _experiment_model = ExperimentModel.objects(id=experiments_id).first()
    if _experiment_model is None:
        return DataLabResponse.inaccessible("The experiment doesn't exist")
    print(data_id)
    response = crud_da.add_digital(data_id, experiments_id, current_user)
    return response


@router.get('/experiments/asset', summary="Access to experimental digital assets")
async def digital_assets_experiments(
        project_id: str,
        skip: int = 0,
        limit: int = 10,
        order_by: Optional[int] = crud_da.OrderByEnum.create_time,
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        current_user: UserModel = Depends(deps.get_current_user)
):
    skip = skip * limit
    _order_by = {1: "-updated_at",  # Time reversal
                 2: "updated_at",  # Time alignment
                 3: "-file_extension",  # Type inversion
                 4: "file_extension",  # Type positive row
                 5: "-name",  # Name alignment
                 6: "name",  # Name alignment
                 7: "-size",  # Size positive row
                 8: "size"}  # Size positive row

    _q = {k: v for k, v in {"name__contains": name, "user": current_user,
                            "project": project_id, "task": task_id}.items() if v is not None}
    _models = ExperimentsDigitalAssetsModel.objects(**_q).order_by(_order_by.get(order_by))
    _data = list()
    # for i in _models:
    #     print(i.to_mongo().to_dict())
    _data = list(map(lambda x:
                     convert_mongo_document_to_schema(x, ExperimentsDigitalAssetsSchema, revers_map=['from_source'],
                                                      revers_id=True), _models))[skip: skip+limit]
    _m = MultilingualGenericsModel.objects(id__contains=project_id)
    print(_m)
    for _ in _m:
        _ms = _.to_mongo().to_dict()
        _ms['is_file'] = True
        _ms['file_extension'] = "object"
        print(_ms)
        _data.append(_ms)
    return DataLabResponse.successful(data=_data, total=len(_data))


@router.get('/experiments/id_set/{project_id}', summary="Access to experimental digital assetsIDset")
async def id_sets(project_id: str,
                  current_user: UserModel = Depends(deps.get_current_user)):
    _models = ExperimentsDigitalAssetsModel.objects(project=project_id, user=current_user)
    if not _models:
        return DataLabResponse.successful(data=list())
    try:
        _ids = [_.from_source.id for _ in _models]
    except Exception as e:
        print(e)
        return DataLabResponse.failed("Acquisition failure")
    return DataLabResponse.successful(data=_ids)


@router.delete('/experiments/asset', summary="Delete the experimental digital assets")
async def delete_experiments_assets(data_id: str,
                                    project_id: str,
                                    current_user: UserModel = Depends(deps.get_current_user)):
    kwargs = dict()
    if "," in data_id:
        data_id = data_id.split(',')
        kwargs["id__in"] = data_id
    else:
        kwargs["id"] = data_id
    ExperimentsDigitalAssetsModel.objects(project=project_id, user=current_user.id, **kwargs).delete()
    return DataLabResponse.successful()


@router.get('/asset')
async def get_digital_assets(
        skip: int = 0,
        limit: int = 10,
        name: str = None,
        data_id: str = None,
        order_by: Optional[int] = crud_da.OrderByEnum.create_time,
        current_user: UserModel = Depends(deps.get_current_user)
):
    if name == "":
        name = None
    if data_id is not None:
        return crud_da.next_depth(order_by, data_id, current_user, skip, limit)
    return crud_da.search(current_user, name, skip, limit, order_by)


@router.put('/asset/rename/{data_id}')
async def update_name_asset_object(data_id: str, name: str, current_user: UserModel = Depends(deps.get_current_user)):
    return crud_da.update(data_id, current_user, name=name)


@router.delete('/asset')
async def remove_asset_object(data_id: str, current_user: UserModel = Depends(deps.get_current_user)):
    return crud_da.delete(data_id, current_user)


# @router.post("/folder/create")
# async def create_dataset_folder(
#         name: str,
#         parent: str,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     """
#     Creating folders（for Analysis sets the output path）
#
#     :param name:
#     :param parent: Parent directory
#     :param current_user:
#     :return:
#     """
#     #
#     dataset_id = generate_uuid(length=26)
#     _parent_model = None
#     if parent != "root":
#         _parent_model = DataFileSystem.objects(id=parent).first()
#         if _parent_model is None:
#             return DataLabResponse.failed("parent dataset not found")
#     # New
#     # targetDFS = DataFileSystem(
#     #     id=dataset_id,
#     #     name=name,
#     #     is_file=False,
#     #     is_dir=True,
#     #     store_name=store_name,
#     #     data_size=0,
#     #     data_path=target_path,
#     #     user=current_user.id,
#     #     from_source="ANALYSIS",  # ANALYSIS Can be displayed at the first level in the data list
#     #     deleted=0,
#     #     created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#     #     updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#     #     data_type="myData",
#     #     storage_service="ext4",
#     #     file_extension=None,
#     #     parent=parent,
#     #     deps=deps  # FIXME: Subdirectory of deps Not yet calculated，Temporary arrangement -1 logo
#     # )
#     # targetDFS.save()
#
#     return DataLabResponse.successful(_data)


@router.post("/download")
async def download_digital_asset(data_id: str = Form(...), current_user: UserModel = Depends(deps.get_current_user)):
    _model = DataFileSystem.objects(id=data_id, user=current_user).first()
    if _model is None:
        DataLabResponse.failed("File does not exist")
    file_name, streaming = DataLakeManager().download(_model)
    return StreamingResponse(
                streaming,
                media_type="application/octet-stream",
                headers={'Content-Disposition': f'attachment; filename={file_name}'}
            )


@router.post("/users/upload/file")
async def upload_file_digital(file: UploadFile = File(...),
                              chunk_number: str = Form(...),  # Current shard
                              identifier: str = Form(...),  # logo
                              total_size: int = Form(...),  # Current total file size
                              relative_path: str = Form(...),  # Absolute path
                              current_user: UserModel = Depends(deps.get_current_user)
                              ):
    _allocated_storage_size = StorageResourceAllocatedModel.objects(allocated_user=current_user.id).\
        first().allocated_storage_size
    _used_storage_size = FileDigital.objects(user=current_user).count("data_size")
    if _allocated_storage_size - _used_storage_size < total_size:
        return DataLabResponse.failed("Insufficient storage space")
    if len(chunk_number) == 0 or len(identifier) == 0:
        return DataLabResponse.failed("logo")
    filename = f'{relative_path}{identifier}{chunk_number}'  # Shardinglogo
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
    return DataLabResponse.successful(msg=f"Received{relative_path}Sharding{chunk_number}")


@router.post("/users/upload/merge")
async def merge_file(identifier: str = Form(...),
                     file_name: str = Form(...),
                     current_user: UserModel = Depends(deps.get_current_user)):
    if len(file_name) == 0 or len(identifier) == 0:
        return DataLabResponse.failed("logo")
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
    #  Push to lake file system
    #  absolute_path = f"{storage_path}/uploads/{file_name}"
    # _model = StorageManager.save_file(absolute_path, file_name, current_user)
    return DataLabResponse.successful(file=file_name)

