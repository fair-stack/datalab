# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:response
@time:2023/06/07
"""
from typing import Optional
from fastapi.responses import JSONResponse
from fastapi import status


class DataLabResponse:

    @staticmethod
    def successful(**kwargs):
        content = dict()
        content["msg"] = "Successful!"
        if kwargs:
            content.update(kwargs)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=content)

    @staticmethod
    def failed(msg: str):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": msg})

    @staticmethod
    def error(msg: str):
        return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            content={"msg": msg})

    @staticmethod
    def inaccessible(msg: str):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": msg})
