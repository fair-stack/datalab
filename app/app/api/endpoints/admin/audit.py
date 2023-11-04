# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:audit
@time:2022/10/31
"""
import uuid
from fastapi import (
    APIRouter,
    Depends,
    status,
)

from fastapi.responses import JSONResponse
from app.models.mongo import UserModel, ExperimentModel, ToolTaskModel,ToolsTreeModel
from app.api import deps
from app.models.mongo.audit_enumerate import AuditEnumerateModel
from app.models.mongo import AuditRecordsModel
from app.schemas import AuditRecordsSchema
from app.utils.common import convert_mongo_document_to_schema
router = APIRouter()


@router.put('/audit/enumerate')
def update_audit_enumerate(audit_type: str,
                           current_user: UserModel = Depends(deps.get_current_user)):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"msg": "API Temporarily unavailable"}
    )


@router.post('/audit/enumerate')
def create_audit_enumerate(audit_type: str,
                           current_user: UserModel = Depends(deps.get_current_user)):
    try:
        AuditEnumerateModel(
            user=current_user.id,
            audit_type=audit_type,
            id=str(uuid.uuid4()),

        ).save()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"msg": "Success"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Audit create error with {e}!"}
        )


@router.delete('/audit/enumerate')
def delete_audit_enumerate(enumerate_id: str,
                           current_user: UserModel = Depends(deps.get_current_user)):
    try:
        AuditEnumerateModel.objects(id=enumerate_id).first().delete()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"msg": "Success"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Audit delete error with {e}!"}
        )

@router.get('/audit')
async def resource_audit(
                         page: int= 0,
                         limit: int=10,
                         name: str = None,
                         audit_result: str = None,
                         audit_type: str = None,
                         current_user: UserModel = Depends(deps.get_current_user)):
    skip = page*limit
    resource_audit_data = \
        list(map(lambda x: convert_mongo_document_to_schema( x, AuditRecordsSchema),
            AuditRecordsModel.objects()))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": resource_audit_data[skip: skip+limit],
                                 "total": len(resource_audit_data)})


