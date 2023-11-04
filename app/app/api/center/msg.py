# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:msg
@time:2022/11/16
"""
from fastapi import (
    APIRouter,
    Depends,
    status,
)
import datetime
from fastapi.responses import JSONResponse
from app.api import deps
from app.models.mongo import (
    UserModel
)

from app.utils.msg_util import find_records
from app.utils.common import convert_mongo_document_to_schema, convert_mongo_document_to_data
from app.models.mongo.messages import MessagesModel
from app.schemas.messages import MessagesSchema
from app.utils.common import generate_uuid
router = APIRouter()


# @router.get('/')
# def personal_msg(
#         title: str = None,
#         page: int = 0,
#         limit: int = 10,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     skip = page*limit
#     _query = dict()
#     if title:
#         _query = {"title__icontains": title}
#     try:
#         _data = list()
#         _set = set()
#         # Whether the current user has permission to approve，Can read all unapproved state Request record information.
#         ls = find_records(current_user.role.permissions)
#         if ls:
#             audit_info = MessagesModel.objects(messages_source__in=ls, **_query)
#             for _ in audit_info:
#                 if _.id not in _set:
#                     _item = convert_mongo_document_to_schema(_, MessagesSchema, revers_map=['user', 'from_user'])
#                     _item['operation_type'] = True
#                     _data.append(_item)
#                     _set.add(_item['id'])
#         msg = MessagesModel.objects(user=current_user.id, **_query, id__nin=_set)
#         for _ in msg:
#             _item = convert_mongo_document_to_schema(_, MessagesSchema, revers_map=['user', 'from_user'])
#             _data.append(_item)
#         return JSONResponse(status_code=status.HTTP_200_OK,
#                             content={"msg": "Success",
#                                      "data": _data[skip: skip+limit],
#                                      "total": len(_data)
#                                      }
#                             )
#     except Exception as e:
#         return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
#                             content={"msg": str(e)})


@router.put('/')
def submit_msg(
        msg_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    MessagesModel.objects(id=msg_id).update_one(unread=False, read_time=datetime.datetime.utcnow())
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"}
                        )


@router.get('/')
def msg_v2( title: str = None,
            page: int = 0,
            limit: int = 10,
            operation: bool = None,
            operation_type:bool = None,
            unread: bool = True,
            current_user: UserModel = Depends(deps.get_current_user)):
    """
    Allocate existing computing resources to a user </br>
    :param user: Specifies the user to obtain the resourceid</br>
    :param base_id: Computing resourcesid</br>
    :param allocated_use_time: Authorized use time In seconds</br>
    :return:
    """
    skip = page*limit
    query = {k: v for k, v in
             {'title__contains': title, "operation": operation, "operation_type": operation_type, "unread": unread}.items()
             if v is not None}
    ls = find_records(current_user.role.permissions)
    audit_msg = list()
    if ls:
        audit_msg = MessagesModel.objects(messages_source__in=ls, **query).order_by('-creat_time')
    msg = MessagesModel.objects(user=current_user.id,**query).order_by('-creat_time')
    _data = []
    for _ in msg:
        _item = convert_mongo_document_to_schema(_, MessagesSchema, revers_map=['user', 'from_user'])
        _data.append(_item)
    if audit_msg:
        for _ in audit_msg:
            _item = convert_mongo_document_to_schema(_, MessagesSchema, revers_map=['user', 'from_user'])
            _data.append(_item)

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _data[skip: skip+limit],
                                 "total": len(_data)})


