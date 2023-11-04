# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:docker_images
@time:2022/08/11
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List
from app.schemas.images import ImagesSchema
from app.models.mongo.images import ImagesModel
from app.utils.docker_util.executor import ContainerManger
router = APIRouter()


@router.get('/', response_model=List[ImagesSchema])
def all_images():
    return [ImagesSchema(**image._data) for image in ImagesModel.objects]


@router.delete('/delete')
def delete_image(image_id: str):
    _data = ContainerManger().delete_image(image_id)
    content = {"code": 0,
               "msg": "success",
               "data": []
               }
    if _data is not None:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={"msg": "Image remove error!"},
        )

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))

