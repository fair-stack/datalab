import os
import json
import datetime
import asyncio
import requests
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
    Request, BackgroundTasks, WebSocket
)
from fastapi.responses import JSONResponse
from pathlib import Path
from app.api import deps
from app.core.config import settings
from app.utils.common import generate_uuid
from app.fair_stack.instdb import InstDBFair
from app.utils.middleware_util import get_s3_client
from app.utils.common import convert_mongo_document_to_schema
from app.models.mongo import UserModel, StorageResourceAllocatedModel
from app.schemas.public_data import PublicDatasetSchema, PublicDataFileSchema
from app.utils.file_util import generate_datasets_model, stream_to_b64_stream, file_upload_task
from app.models.mongo.public_data import PublicDatasetModel, PublicDataFileModel, DatasetsAuthorModel,PublicDatasetOptionModel
from app.service.manager.storage import StorageManager
router = APIRouter()


def instdb_log(url, dataset_id):
    image_path = settings.BASE_DIR + '/' + dataset_id + url.split('/')[-1]
    with open(image_path, 'wb') as f:
        print(image_path)
    # with open( url.split('/')[-1], 'wb') as f:
        f.write(requests.get(url).content)
    # with open(pathlib.Path(settings.BASE_DIR, dataset_id, url.split('/')[-1]).as_posix(), 'rb') as f:
    return open(image_path, 'rb')


@router.post('/', summary="Creating public Data")
async def create_public_data(name: str,
                             label: str,
                             description: str,
                             data_type: str,
                             icon: UploadFile = File(...),
                             current_user: UserModel = Depends(deps.get_current_user)):
    if name is not None:
        if PublicDatasetModel.objects(name=name).first() is not None:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "Expose duplicate data source names！"})
    dataset_id = generate_uuid()
    client = get_s3_client()
    if not client.bucket_exists(dataset_id):
        client.make_bucket(dataset_id)
    result = client.put_object(
        bucket_name=dataset_id,
        object_name=f'/icon/{icon.filename}',
        data=icon.file,
        length=-1,
        content_type="application/octet-stream",
        part_size=10 * 1024 * 1024
    )
    object_name = result.object_name
    public_ds = PublicDatasetModel(id=dataset_id,
                                   name = name,
                                   label=label,
                                   description=description,
                                   data_type=data_type,
                                   icon=object_name,
                                   user=current_user.id)
    public_ds.save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={'msg': "Successful!"})


@router.get('/', summary="Access to open data")
async def get_public_data(name: str = None,
                          page: int = 0,
                          limit: int = 10,
                          current_user: UserModel = Depends(deps.get_current_user)):
    client = get_s3_client()
    if name:
        _dfs = PublicDatasetModel.objects(name__contains=name)
    else:
        _dfs = PublicDatasetModel.objects
    data = list()
    for _ in _dfs.order_by("-updated_at"):
        _d = convert_mongo_document_to_schema(_, PublicDatasetSchema)
        _d['icon'] = stream_to_b64_stream(client.get_object(_.id, _.icon).read())
        _files = PublicDataFileModel.objects(datasets=_)
        _files_count = 0
        _files_size = 0
        for _f in _files:
            if _f.file_extension == "datasets":
                _datasets_files = PublicDataFileModel.objects(datasets=_f)
                _files_size += _datasets_files.sum('data_size')
                _files_count += _datasets_files.count()
            else:
                _files_count += 1
                _files_size += _f.data_size
        _d['files'] = _files_count
        print([_f.data_size for _f in _files])
        _d['data_size'] = _files_size
        data.append(_d)
    skip = page * limit
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": data[skip: skip+limit],
                                 "total": len(data),
                                 "msg": "Successful!"})


@router.delete('/', summary="Deleting Public Data")
async def delete_public_data(
        dataset_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    _d = PublicDatasetModel.objects(id=dataset_id).first()
    if _d is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Dataset not found!"})
    _d.delete()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.put('/', summary="Modifying public data")
async def update_public_data_metadata(dataset_id: str,
                                      name: str = None,
                                      label: str = None,
                                      data_type: str = None,
                                      description: str = None,
                                      access: str = None,
                                      icon: UploadFile = File(None),
                                      current_user: UserModel = Depends(deps.get_current_user)
                                      ):
    _d = PublicDatasetModel.objects(id=dataset_id).first()
    if _d is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Dataset not found!"})
    if name is not None:
        if PublicDatasetModel.objects(name=name, id__ne=dataset_id).first() is not None:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "Expose duplicate data source names！"})
    object_name = None
    if icon:
        client = get_s3_client()
        if not client.bucket_exists(dataset_id):
            client.make_bucket(dataset_id)
        result = client.put_object(
            bucket_name=dataset_id,
            object_name=f'/icon/{icon.filename}',
            data=icon.file,
            length=-1,
            content_type="application/octet-stream",
            part_size=10 * 1024 * 1024
        )
        object_name = result.object_name
    update_params = {k: v for k, v in {"name": name, "label": label, "data_type": data_type,
                                       "description": description, "access": access,
                                       "icon": object_name}.items() if v is not None}

    _d.update(**update_params)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.post('/options', summary="Whether to make public datasets available to users")
async def public_option(
        option: bool,
        current_user: UserModel = Depends(deps.get_current_user)
):
    _d = PublicDatasetOptionModel.objects.first()
    if _d is None:
        PublicDatasetOptionModel(id=generate_uuid(),
                                 access=option,
                                 user=current_user.id
                                 ).save()
    else:
        print(_d)
        _d.update(access=option)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.get('/options', summary="Whether to make public datasets available to users")
async def public_option(
        current_user: UserModel = Depends(deps.get_current_user)
):
    _d = PublicDatasetOptionModel.objects.first()
    _status = None
    if _d is None:
        PublicDatasetOptionModel( id = generate_uuid(),
                                 access = True,
                                 user = current_user.id
                                 ).save()
        _status = True
    else:
        _status = _d.access
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "data": _status})


@router.post('/data', summary="Upload the data file to the public dataset")
async def add_dataset_file(request: Request,
                           background_tasks: BackgroundTasks,
                           dataset_id: str,
                           description: str = "",
                           file: UploadFile = File(...),
                           current_user: UserModel = Depends(deps.get_current_user)):
    update = False
    _search = PublicDataFileModel.objects(datasets=dataset_id, name=file.filename)
    _pd = PublicDatasetModel.objects(id=dataset_id)
    if _pd.first() is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Create file model mismatch Datasets"})
    if _search.first():
        update = True
        data_id = _search.first().id
    else:
        data_id = generate_uuid()
    background_tasks.add_task(file_upload_task, *(request.app.state.file_upload, dataset_id, file,
                                                  description, data_id, update, _search, _pd, current_user.id))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!", "id": data_id})


@router.post('/datasets', summary="Creating public Data")
async def create_datasets_from_source(
        source_id: str = Form(...),
        name: str = Form(...),
        description: str = Form(...),
        current_user: UserModel = Depends(deps.get_current_user)):
    if PublicDataFileModel.objects(name=name, datasets=source_id).first() is not None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Duplicate dataset names！"})
    try:
        datasets_id = generate_uuid()
        datasets_model = PublicDataFileModel(
                id=datasets_id,
                datasets=source_id,
                name=name,
                data_path=datasets_id,
                data_size=9,
                user=current_user,
                store_name=datasets_id,
                description=description,
                from_source="PUBLIC",
                data_type="DATASETS",
                is_file=True,
                storage_service="oss",
                file_extension="datasets",
                deps=0
            )
        datasets_model.save()
        client = get_s3_client()
        client.make_bucket(datasets_id)
        storage_path = Path(settings.BASE_DIR, settings.DATA_PATH)
        mks_name = f"{storage_path}/uploads_datasets_cache/{datasets_id}"
        os.makedirs(mks_name)
    except Exception as e:
        print(f"Creating public Data，Cause of exception: {e}.{current_user.name}: {source_id}")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Dataset creation failed!"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!", "id": datasets_id})


@router.post("/datasets/upload_file", summary="Upload the data file to the dataset under the public data source")
async def upload_big_file(
        datasets_id: str = Form(...),
                          file: UploadFile = File(...),
                          chunk_number: str = Form(...),  # Current shard
                          identifier: str = Form(...),  # Unique identification
                          total_size: int = Form(...),  # Current total file size
                          total_chunks: int = Form(...),  # Total number of slices in the current file
                          relative_path: str = Form(...),  # Absolute path
                          current_chunk_size: int = Form(...),  # Total upload size
                          current_user: UserModel = Depends(deps.get_current_user)
                          ):  # Shard upload file [with unique identifier+Shard sequence number  as the filename
    if len(chunk_number) == 0 or len(identifier) == 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Missing identifier"})
    filename = f'{relative_path}{identifier}{chunk_number}'  # ShardingUnique identification
    contents = await file.read()  # Read a file asynchronously
    storage_path = Path(settings.BASE_DIR, settings.DATA_PATH)
    _path = Path(filename)
    if _path.parent != "." and _path.parent != "/":
        mks_name = f"{storage_path}/uploads_datasets_cache/{datasets_id}/{_path.parent}"
        try:
            os.makedirs(mks_name)
        except FileExistsError:
            pass
    with open(f"{storage_path}/uploads_datasets_cache/{datasets_id}/{filename}", "wb") as f:
        f.write(contents)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": f"Received{relative_path}Sharding{chunk_number}"})


@router.post("/datasets/merge_file")
async def merge_file(
        request: Request,
        background_tasks: BackgroundTasks,
        datasets_id: str = Form(...),
        identifier: str = Form(...),
        file_name: str = Form(...),
        chunk_star: int = Form(...),  # Unique identification
        current_user: UserModel = Depends(deps.get_current_user)):
    if len(file_name) == 0 or len(identifier) == 0:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Missing identifier"})
    storage_path = Path(settings.BASE_DIR, settings.DATA_PATH)
    _mode_base = f"{file_name}{identifier}*"
    _mode_path = f"{storage_path}/uploads_datasets_cache/{datasets_id}"
    if len(file_name.split('/')) > 1:
        _mode_base = f"{file_name.rsplit('/', maxsplit=1)[-1]}{identifier}*"
        _mode_path = f"{storage_path}/uploads_datasets_cache/{datasets_id}/{file_name.rsplit('/', maxsplit=1)[0]}"
        print("intercept", _mode_path)
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
    absolute_path = f"{storage_path}/uploads_datasets_cache/{datasets_id}/{file_name}"
    client = get_s3_client()
    StorageManager.save_datasets_file(absolute_path, file_name, datasets_id, current_user, client)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"file": file_name, "msg": "Successful!"})


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


@router.put('/datasets/{datasets_id}', summary="Change the dataset information")
async def get_datasets_file(
        dataset_id: str,
        name: str = None,
        description: str = None,
        current_user: UserModel = Depends(deps.get_current_user)):
    _dfs = PublicDataFileModel.objects(id=dataset_id).first()
    if _dfs is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "The dataset does not exist！"})
    if name:
        if PublicDataFileModel.objects(name=name, datasets=_dfs.datasets, id__ne=dataset_id).first() is not None:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "Duplicate dataset names！"})
        _dfs.name = name
    if description:
        _dfs.description = description
    _dfs.updated_at = datetime.datetime.utcnow()
    _dfs.save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.get('/data', summary="Access to open data")
async def get_public_file(
        dataset_id: str,
        name: str = None,
        file_extension: str=None,
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


@router.websocket("/ws/{data_id}")
async def socket_analysis(websocket: WebSocket, data_id: str):
    await websocket.accept()
    while 1:
        # Collection of component states
        import redis

        _data = await websocket.app.state.file_upload.get(data_id)
        await websocket.send_json(json.loads(_data))
        await asyncio.sleep(1)
    await websocket.close()


@router.post('/instdb', summary="InstDBInteroperate to obtain data set information")
async def instdb_link(
        url: str,
        secret_key: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    client = get_s3_client()
    inst_cls = InstDBFair.create_link(url, secret_key)
    if inst_cls is not None:
        lis = []
        _datasets = inst_cls.datasets_meta_data()
        if _datasets:
            for _, _file in _datasets:
                dataset_id = _['id']
                if not client.bucket_exists(dataset_id):
                    client.make_bucket(dataset_id)
                result = client.put_object(
                    bucket_name=dataset_id,
                    object_name=f'/icon/{_["icon"].split("/")[-1]}',
                    data=instdb_log(_['icon'], dataset_id),
                    length=-1,
                    content_type="application/octet-stream",
                    part_size=10 * 1024 * 1024
                )
                object_name = result.object_name
                _['icon'] = object_name
                authors = list()
                for _author in _.pop('author'):
                    authors.append(DatasetsAuthorModel(**_author))
                _['author'] = authors
                public_ds = PublicDatasetModel(user=current_user.id,data_type="INSTDB", **_)
                public_ds.save()
                if _file:
                    for _f in _file:
                        if _f:
                            PublicDataFileModel(
                                id=generate_uuid(),
                                datasets=dataset_id,
                                name=_f['name'],
                                data_path=_f['data_path'],
                                data_size=_f['data_size'],
                                user=current_user.id,
                                store_name=dataset_id,
                                description="",
                                from_source="INSTDB",
                                data_type="UNDETERMINED",
                                is_file=not _f['is_dir'],
                                storage_service="ftp",
                                file_extension=_f['name'].rsplit('.', maxsplit=1)[-1],
                                deps=len(_f['data_path'].split('/')) - 2
                            ).save()
                _.pop('author')
                lis.append(_)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": lis,
                                     "msg": "Successful"})
    else:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Failure in link InstDb"})


@router.put('instdb', summary="Select ImportInstDBWhich datasets?,Passed into the datasetid")
async def instdb_link(
        datasets_id: list,
        current_user: UserModel = Depends(deps.get_current_user)):
    try:
        PublicDatasetModel.objects(id__in=datasets_id).update(access="PUBLIC")
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"Failure in choice datasets {e}"})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful"})


@router.delete('/datasets/{dataset_id}', summary="Delete the data set under the data source")
async def delete_source_datasets(dataset_id: str,
                                 current_user: UserModel = Depends(deps.get_current_user)):
    _dfs = PublicDataFileModel.objects(id=dataset_id).first()
    if _dfs is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "The dataset does not exist！"})
    _dfs.delete()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful！"})


@router.delete('/datasets/{datasets_id}/{file_id}', summary="Delete the data set under the data source")
async def delete_source_datasets_file(datasets_id: str, file_id: str,
                                      current_user: UserModel = Depends(deps.get_current_user)):
    _dfs = PublicDataFileModel.objects(datasets=datasets_id, id=file_id).first()
    if _dfs is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Data file does not exist！"})
    _dfs.delete()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful！"})
