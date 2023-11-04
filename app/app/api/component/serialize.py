# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:serialize
@time:2023/02/02
"""
import pickle
from fastapi import (
    APIRouter,
    Depends,
    status,

)

from fastapi.responses import JSONResponse
from app.api import deps
from app.models.mongo import UserModel
from app.core.serialize.ptype import frontend_map
from app.utils.middleware_util import get_s3_client
from minio import S3Error
from app.core.faas import FaaSEventGenerator
from app.core.note.note_factory import NoteBookFactory
router = APIRouter()


@router.post('/test/{function_name}')
async def component_start(
        function_name: str,
        data: dict = {}
        # current_user: UserModel = Depends(deps.get_current_user)
):
    FaaSEventGenerator('123456', function_name, **data).generator_inputs()
    return {}


@router.post('/notebook')
async def create_notebook(app_id: str):
    nb = NoteBookFactory(app_id)
    nb.create_notebook()
    nb.register_service()
    return {}
# @router.get('/')
# async def serialize_functions(lab_id: str,
#                               task_id: str = None,
#                               current_user: UserModel = Depends(deps.get_current_user)):
#
#     client = get_s3_client()
#     if task_id:
#         try:
#             _io = client.get_object(lab_id, task_id + '/' + "labVenvData.pkl")
#             try:
#                 _object = pickle.load(_io)
#             except Exception as e:
#                 _object = ""
#             # Can beJsonTransfer format validation, coercionstr __str__
#             _structure = frontend_map(_object, f"{lab_id}_{task_id}")
#         except S3Error:
#             return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
#                                 content={"msg": "The data has been released！"})
#
#     else:
#         _structure = list()
#         try:
#             for _ in client.list_objects(lab_id):
#                 try:
#                     _io = client.get_object(lab_id, _.object_name + "labVenvData.pkl")
#                 except S3Error:
#                     pass
#                 try:
#                     _object = pickle.load(_io)
#                 except Exception as e:
#                     print(f"Serialization exception {e}: {lab_id}/{_.object_name}")
#                     _object = None
#                 _structure.append(
#                     frontend_map(_object, f"{lab_id}_{_.object_name.replace('/', '')}")
#                     )
#         except S3Error:
#             pass
#         return JSONResponse(status_code=status.HTTP_200_OK,
#                             content={"data": _structure,
#                                      "msg": "Successful!"}
#                             )
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"data": _structure,
#                                  "msg": "Successful!"}
#                         )
