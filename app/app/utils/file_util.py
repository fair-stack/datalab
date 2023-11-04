import logging
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Union
import pathlib
from fastapi import UploadFile, File
from app.core.config import settings
import os
from app.utils.resource_util import cache_cumulative_sum, cut_user_storage_size
from app.utils.uploads3_util import main as loadingfile
from app.models.mongo import DataFileSystem, UserModel
from app.utils.common import generate_uuid
from app.models.mongo.public_data import PublicDataFileModel, PublicDatasetModel
from app.utils.middleware_util import get_s3_client
import datetime
import base64

"""
File operations

ref: https://pyquestions.com/how-to-save-uploadfile-in-fastapi
"""


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    try:
        _file = upload_file.file
        _file.seek(0)
        with destination.open("wb") as buffer:
            shutil.copyfileobj(_file, buffer)
    finally:
        upload_file.close()
        upload_file.file.close()


def chunked_copy(src: BinaryIO, dest: Union[str, Path], chunk_size=2 ** 20) -> None:
    """
    Copying files
    :param src: file-like object
    :param dest:
    :param chunk_size:
    :return:
    """
    src.seek(0)
    with open(dest, "wb") as buffer:
        while True:
            content = src.read(chunk_size)
            if not content:
                # print("src completely consumed.")
                break
            # print(f"Consumed {len(content)} bytes from src file")
            buffer.write(content)


def clean_after_fail_parse_tool_zip(zipfile_name: str,
                                    zip_path: str = str(Path(settings.BASE_DIR, settings.TOOL_ZIP_PATH)),
                                    unzip_path: str = str(Path(settings.BASE_DIR, settings.TOOL_PATH)),
                                    user_space: str = "",
                                    ) -> None:
    """
    After parsing fails，Deleting source files
    :param zipfile_name:
    :param zip_path:
    :param unzip_path:
    :param user_space:
    :return:
    """
    # Delete tool.zip
    source_path = Path(zip_path, user_space, zipfile_name)
    if source_path.exists() and source_path.is_file():
        logging.info(f"deleting file: {source_path}")
        source_path.unlink()
        logging.info(f"deleted file: {source_path}")
    # Delete unzipped_dir
    dir_name = zipfile_name.removesuffix(".zip")
    unzipped_path = Path(unzip_path, user_space, dir_name)
    if unzipped_path.exists() and unzipped_path.is_dir():
        logging.info(f"deleting dir: {unzipped_path}")
        shutil.rmtree(unzipped_path)
        logging.info(f"deleted dir: {unzipped_path}")


def insert_one(user_id, data: dict):
    his = DataFileSystem.objects(name=data['name'], user=user_id)
    if his.first():
        his.update_one(data_size=data['size'])
    else:
        DataFileSystem(id=generate_uuid(), name=data['name'], is_file=not data['is_dir'], store_name=data['name'],
                       data_size=data['size'],
                       data_path=data['name'], from_source="UPLOADED", deleted=0,
                       created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       updated_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                       data_type="myData", alias_name=data['alias_name'],
                       parent=data['parent'], child=data['child'], is_dir=data['is_dir'],
                       deps=data['deps'], file_extension=data['format'] if data.get('format') else "",
                       user=user_id
                       ).save()


def get_img_b64_stream(img_local_path: Union[str, Path]):
    """
    Get the local image stream
    :param img_local_path: The absolute path to the image
    :return:
    """
    import base64

    path = Path(img_local_path)
    stream = b''
    if not (path.exists() and path.is_file()):
        return stream
    with open(path, "rb") as f:
        stream = f.read()
        stream = base64.b64encode(stream)
    return stream


def convert_uploaded_img_to_b64_stream_str(src: BinaryIO) -> str:
        """
        Convert the uploaded file to base64 bytes，And then convert to str，Easy to persist

        :param src: file-like object
        :return:
        """
        stream = ""
        content = src.read()
        if content:
            stream = base64.b64encode(content).decode()     # with .decode
            return stream
        else:
            return stream


def convert_base64_str_to_bytes(img_str: str):
    """
    Will be persistent base64 str, Convert into base64 bytes

    :param img_str:
    :return:
    """
    if img_str:
        resp = img_str.encode()
        return resp
    else:
        return ''


async def generate_dir(source, data_type, deps=1, storage_path: str = "", inc_con=None, user_id=None):
    _different = len(pathlib.Path(source).parents) - 1
    storage_path = storage_path + '/'
    if pathlib.Path(source).is_dir():
        deps_map = dict()
        deps_map[_different] = dict()
        deps_map[_different][source] = {
            "name": source,
            "alias_name": 'root',
            "parent": None,
            "child": [],
            "size": 0,
            "is_dir": "True",
            "data_type": data_type,
            "deps": _different

        }
        file_list = list()
        for root, dirs, files in os.walk(source):
            for _dir in dirs:
                sub_dir_name = os.path.join(root, _dir)
                sub_dir_path = pathlib.Path(sub_dir_name)
                parent_name = sub_dir_path.parent.__fspath__()
                inner_deps = len(sub_dir_path.parents) - deps
                if deps_map.get(inner_deps) is None:
                    deps_map[inner_deps] = dict()
                deps_map[inner_deps][sub_dir_name] = {"name": sub_dir_name,
                                                      "alias_name": sub_dir_name[1:],
                                                      "parent": parent_name,
                                                      "child": [],
                                                      "size": 0,
                                                      "is_dir": "true",
                                                      "data_type": data_type,
                                                      "deps": inner_deps}
            for name in files:
                sub_file_name = os.path.join(root, name)
                sub_path = pathlib.Path(sub_file_name)
                parent_name = sub_path.parent.__fspath__()
                child = list()
                file_list.append({"name": sub_file_name, "alias_name": sub_file_name.replace(source, '')[1:],
                                  "parent": parent_name, "child": child, "size": sub_path.stat().st_size,
                                  "is_dir": "false",
                                  "data_type": data_type, "deps": len(sub_path.parents) - deps,
                                  "format": sub_path.suffix.rsplit('.', maxsplit=1)[-1]})

        def inner_add(base, size, add_child=None):
            base['size'] += size
            if base['deps'] > _different:
                parent = deps_map[base['deps'] - 1][base['parent']]
                parent["size"] += size
                if add_child:
                    parent["child"].append(base["name"])
                if parent['parent'] is not None and parent['deps'] > 0:
                    inner_add(deps_map[parent['deps'] - 1][parent['parent']], size)

        file_list.sort(key=lambda x: x['deps'], reverse=True)
        for _ in file_list:
            parent_dir_deps = _['deps'] - 1
            # Bottom-up aggregationsize
            parend_dir = deps_map[parent_dir_deps][_['parent']]
            inner_add(parend_dir, _['size'])
            parend_dir['child'].append(_['name'])
        deps_map[_different][source]['parent'] = "root"
        for _ in file_list:
            _['child'] = _['child']
            _['name'] = _['name'].replace(storage_path, "")
            _['parent'] = _['parent'].replace(storage_path, "")
            _['deps'] = _['deps'] - _different
            # DataFileSystem(**_).save()
            insert_one(user_id, _)
        for v in deps_map.values():
            for _v in v.values():
                _v['name'] = _v['name'].replace(storage_path, "")
                _v['parent'] = _v['parent'].replace(storage_path, "")
                _v['deps'] = _v['deps'] - _different
                # print(_v)
                # DataFileSystem(**_v).save()
                insert_one(user_id, _v)

        await cache_cumulative_sum(user_id, deps_map[_different][source]["size"],
                                   f"{deps_map[_different][source]['name']}", inc_con)
    else:
        _size = pathlib.Path(source).stat().st_size
        _ = {"name": source.replace(storage_path, ""),
             "alias_name": source.replace(storage_path, ""),
             "parent": "root",
             "child": [],
             "size": _size,
             "is_dir": "false",
             "data_type": data_type,
             "deps": 0,
             "format": pathlib.Path(source).suffix.rsplit('.', maxsplit=1)[-1]}
        # DataFileSystem(**_).save()
        insert_one(user_id, _)
        await cache_cumulative_sum(user_id, _size,
                                   _['name'], inc_con)


def generate_datasets_model(dataset_id, user_id, datasets_id=None):
    if datasets_id is None:
        datasets_id = []
    datasets_id.append(dataset_id)
    _d = DataFileSystem.objects(id=dataset_id).first()
    if _d is not None:
        deps = _d.deps + 1
        name = _d.name
        _dfs = DataFileSystem.objects(user=user_id, deps=deps).filter(
            __raw__={'name': {'$regex': f'.*{name}*'}})
        for _ in _dfs:
            _p = DataFileSystem.objects(id=_.id).first()
            generate_datasets_model(_p.id, user_id, datasets_id)

    return datasets_id


def share_util(data_model: DataFileSystem, to_user: UserModel, user: UserModel):
    replica_data = list()
    # if data_model.is_dir:
    _dfs = DataFileSystem.objects(user=data_model.user.id).filter(
        __raw__={'data_path': {'$regex': f'.*{data_model.data_path}*'}})
    new2old = dict()
    for i in _dfs:
        item = i.to_mongo().to_dict()
        key = item.pop('_id')
        item['id'] = generate_uuid()
        new2old[key] = item['id']
        item['user'] = to_user
        item['public'] = "PRIVATE"
        item['from_user'] = user
        item['from_source'] = i.id
        item['lab_id'] = None
        item['task_id'] = None
        replica_data.append(item)
    for i in replica_data:
        if i.get("parent") != "root":
            i['parent'] = new2old.get(i['parent'])

        DataFileSystem(**i).save()







def stream_to_b64_stream(stream: BinaryIO):
    """
    Get the local image stream
    :param img_local_path: The absolute path to the image
    :return:
    """
    stream = base64.b64encode(stream)
    return stream.decode()


async def file_upload_task(con, dataset_id, file, description, data_id, update, _search,
                           _pd, user_id, public_file_type: str = "data"):
    await con.set(f"{data_id}-task", 'PENDING')
    client = get_s3_client()
    storage_dir = pathlib.Path(settings.BASE_DIR, 'datasets', data_id)
    storage_path = pathlib.Path(storage_dir, file.filename)
    if not storage_dir.exists():
        storage_dir.mkdir(parents=True)
    with open(storage_path, 'wb') as f:
        f.write(file.file.read())
    # if not client.bucket_exists(dataset_id):
    #     client.make_bucket(dataset_id)
    result = loadingfile(client, dataset_id, f'/{public_file_type}/{file.filename}', storage_path, data_id)
    object_name = result.object_name
    stat = client.stat_object(bucket_name=dataset_id, object_name=object_name)
    size = stat.size
    _new_name = file.filename.split('/')
    try:
        if update:
            _search.update_one(updated_at=datetime.datetime.utcnow(), description=description, data_size=size)
            _pd.update_one(data_size=abs(_pd.first().data_size - _search.first().data_size) + size)
        else:
            public_ds = PublicDataFileModel(
                id=data_id,
                datasets=dataset_id,
                name=file.filename,
                data_path=object_name,
                data_size=size,
                user=user_id,
                store_name=dataset_id,
                description=description,
                from_source="PUBLIC",
                data_type="LOCAL",
                is_file=True,
                storage_service="oss",
                file_extension=file.filename.rsplit('.', maxsplit=1)[-1],
                deps=len(_new_name) - 1
            )
            public_ds.save()
            old_files = _pd.first().files
            old_size = _pd.first().data_size
            _pd.update_one(files=old_files + 1 if old_files else 1,
                           data_size=size if old_size is None else old_size + size)
    except Exception as e:
        await con.set(f"{data_id}-task", 'ERROR')
        await con.set(f"{data_id}", str(e))
    else:
        await con.set(f"{data_id}-task", 'SUCCESS')


async def del_datasets(datasets_id: Union[list, str], user: UserModel, redis_con):
    if isinstance(datasets_id, list):
        _files = DataFileSystem.objects(id__in=datasets_id, user=user)
        update_set = list()
        update_set.extend(datasets_id)
        cut_size = 0
        for _f in _files:
            # Individual additions and uploads are impossible to duplicate
            if _f.data_type == "myData":
                all_subset = DataFileSystem.objects(user=user, data_path__contains=_f.data_path)
                for subset in all_subset:
                    update_set.append(subset.id)
            # The calculated output data may be duplicated
            else:
                all_subset = DataFileSystem.objects(user=user, lab_id=_f.lab_id, task_id=_f.task_id,
                                                    data_path__contains=_f.data_path)
                for subset in all_subset:
                    update_set.append(subset.id)
            try:
                cut_size += _f.data_size
            except Exception as e:
                print(e)
                pass
        # 1. Cut down on personal resources, 2.Delete
        DataFileSystem.objects(id__in=update_set).update(deleted=True)
    else:
        _files = DataFileSystem.objects(id=datasets_id, user=user).first()
        cut_size = 0
        try:
            cut_size += _files.data_size
        except Exception as e:
            print(e)
    state = await cut_user_storage_size(user.id, cut_size, redis_con)
    if state is False:
        raise ValueError("Delete")
