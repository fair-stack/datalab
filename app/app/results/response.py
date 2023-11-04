# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:response
@time:2023/05/17
"""
from fastapi.responses import JSONResponse
from fastapi import status
from typing import Optional


class DataLabResponse:

    @staticmethod
    def successful(**kwargs):
        content = {"msg": "Successful!"}
        content.update(kwargs)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=content)

    @staticmethod
    def failed(msg: str, data: Optional[str] = None):
        content = {"msg": msg, "data": "Client request exception" if data is None else data}
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)

    @staticmethod
    def error(msg: str, data: Optional[str] = None):
        content = {"msg": msg, "data": "Service request processing exception" if data is None else data}
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)

    @staticmethod
    def resources_transgression(msg: str):
        content = {"msg": msg}
        return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, content=content)
