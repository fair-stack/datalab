# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:object_storage
@time:2022/09/05
"""
import pathlib
from urllib.parse import quote
import asyncio
from minio import Minio
from fastapi import status
from fastapi.responses import StreamingResponse, JSONResponse
from app.utils.middleware_util import get_s3_client, s32dir_tree
from app.storage.compress_file import compress_files2zip


async def oss_file_stream(bucket: str, object_name: str, client: Minio, base_dir: str):
    _data = client.get_object(bucket, object_name).read()
    return {"data": _data, "name": object_name.replace(base_dir, '')}


async def object_storage_stream(lab_id, object_name):
    client = get_s3_client()
    object_name = object_name[:-1] if object_name[-1] == "/" else object_name
    lis_obj = list(client.list_objects(lab_id, prefix=object_name))
    if list(lis_obj) and lis_obj[0].is_dir:
        tasks = list()
        _d = s32dir_tree(lab_id, object_name, client=client, recursive=True)
        for _ in _d:
            tasks.append(asyncio.create_task(oss_file_stream(lab_id, _['data_path'], client, object_name)))
        await asyncio.wait(tasks)
        result_response = await compress_files2zip(object_name.rsplit('/')[-1], [_.result() for _ in tasks])
    else:
        def singe_file(lab_id, file_path):
            try:
                yield from client.get_object(lab_id, file_path)
            except:
                yield from client.get_object(lab_id, '/'.join(file_path[1:].split('/')[1:]))
        try:
            file_name = quote(object_name.rsplit('/', maxsplit=1)[-1])
            "decoding"
            # "attachment; filename*=UTF-8''{}".format(escape_uri_path(filename))
            result_response = StreamingResponse(
                singe_file(lab_id, object_name),
                media_type="application/octet-stream",
                headers={'Content-Disposition': f'attachment; filename={file_name}'}
            )
        except Exception as e:
            print(e)
            result_response = JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                           content={'msg': "File does not exist！"})
    return result_response

if __name__ == '__main__':
    ...
