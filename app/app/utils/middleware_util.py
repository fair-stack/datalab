# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:redis_pub
@time:2022/08/30
"""
import hashlib

import redis
from minio import Minio

from app.core.config import settings


def get_parent_dir(file_path):
    if file_path[-1] == '/':
        file_path = file_path[: -1]
    _path = file_path.split('/')
    if len(_path) > 2:
        return '/'.join(_path[:-1]) + '/'
    return None


def get_redis_con(db):
    return redis.Redis(host=settings.REDIS_HOST, db=db)


def get_s3_client():
    return Minio(settings.MINIO_URL,
                 access_key=settings.MINIO__ACCESS_KEY,
                 secret_key=settings.MINIO_SECRET_KEY,
                 secure=settings.MINIO_SECURE)


def s32dir_tree(task_id, iter_dep=None, client=None, recursive=False):
    _d = list()
    if client is None:
        client = get_s3_client()
    if iter_dep is not None and iter_dep[-1] != '/':
        iter_dep += '/'
    if not client.bucket_exists(task_id):
        return _d
    object_list = client.list_objects(task_id, prefix=iter_dep, recursive=recursive)
    for obj in object_list:
        file_parent = get_parent_dir(obj.object_name)
        if file_parent is not None:
            parent_name = file_parent.split('/')[-1]
        else:
            parent_name = None
        if obj.is_dir:
            oname = obj.object_name[:-1].split('/')[-1] if obj.object_name.endswith('/') else \
            obj.object_name.split('/')[-1]
            md5hash = hashlib.md5(oname.encode())
            md5 = md5hash.hexdigest()

            _d.append({
                "_id": md5,
                "created_at": None,
                "data_path": obj.object_name,
                "deleted": False,
                "from_source": "Task",
                "is_file": False,
                "name": oname,
                "num": 0,
                "store_name": oname,
                "data_type": "taskData",
                "updated_at": None,
                "user": task_id,
                "parent_dir": file_parent,
                "parent_name": parent_name,
                "storage_service": "oss"
            })
        else:
            _d.append({
                "_id": obj.etag,
                "created_at": obj.last_modified.strftime('%Y/%m/%d %H:%M:%S'),
                "data_path": obj.object_name,
                "deleted": False,
                "from_source": "Task",
                "is_file": True,
                "name": obj.object_name.split('/')[-1],
                "num": 0,
                "store_name": obj.object_name.split('/')[-1],
                "updated_at": obj.last_modified.strftime('%Y/%m/%d %H:%M:%S'),
                "user": task_id,
                "data_type": "taskData",
                "file_extension": obj.object_name.rsplit('.',maxsplit=1)[-1].lower(),
                "parent_dir": file_parent,
                "parent_name": parent_name,
                "storage_service": "oss"
            })
    return _d



if __name__ == '__main__':
    ...
