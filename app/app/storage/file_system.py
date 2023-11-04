# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:file_system
@time:2022/09/05
"""
import asyncio
import pathlib
from urllib.parse import quote
from fastapi import status
from fastapi.responses import JSONResponse, StreamingResponse
from app.storage.compress_file import compress_files2zip


async def file_stream(file_path, data_path):
    with open(file_path, 'rb') as f:
        _data = f.read()
    if data_path and data_path[-1] != '/':
        data_path += '/'
    relative_paths = file_path.replace(data_path, '')
    return {"data": _data, "name": relative_paths}


async def file_storage_stream(data_path, file_name=None):
    _file_path = pathlib.Path(data_path)
    if not _file_path.exists():
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={'msg': "File does not exist！"})
    if _file_path.is_dir():
        tasks = list()
        for _ in _file_path.iterdir():
            _ = _.__str__()
            tasks.append(asyncio.create_task(file_stream(_, data_path)))
        await asyncio.wait(tasks)
        result_response = await compress_files2zip(_file_path.name, [_.result() for _ in tasks])
        return result_response

    def singe_file(file_path):
        with open(file_path, 'rb') as f:
            yield from f
    if file_name is None:
        file_name = data_path.rsplit('/',maxsplit=1)[-1]
    return StreamingResponse(
        singe_file(data_path),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment;filename={quote(file_name)}"}
    )
