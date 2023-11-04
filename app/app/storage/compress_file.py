# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:compress_file
@time:2022/09/05
"""
import zipfile
from urllib.parse import quote
from io import BytesIO
from typing import List, Dict
from fastapi.responses import StreamingResponse


async def compress_files2zip(dir_name: str, file_objects: List[Dict]):
    zip_file_name = "%s.zip" % dir_name
    file_object = BytesIO()
    with zipfile.ZipFile(file_object, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for _ in file_objects:
            zip_file.writestr(_['name'], _['data'])
        zip_file.close()
        ""
        "application/x-zip-compressed"
    return StreamingResponse(
        iter([file_object.getvalue()]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment;filename={quote(zip_file_name)}"}
    )

if __name__ == '__main__':
    ...
