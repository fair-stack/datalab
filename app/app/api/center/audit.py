# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:audit
@time:2022/10/31
"""
from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.responses import JSONResponse
from app.schemas.audit_records import ComponentsAuditRecordsSchema
from app.api import deps
from app.models.mongo import (
    UserModel,
    AuditEnumerateModel,
    AuditRecordsModel
)
from app.schemas import (
    AuditEnumerateSchema,
    AuditRecordsSchema
)
from app.utils.msg_util import find_records
from app.utils.common import convert_mongo_document_to_schema, convert_mongo_document_to_data


router = APIRouter()


@router.get('/audit/enumerate')
def enumerate_audit_desc(current_user: UserModel = Depends(deps.get_current_user)):
    """
    Enumerates the audit type </br>
    """
    _d = AuditEnumerateModel.objects
    _data = list(map(lambda x: convert_mongo_document_to_schema(x, AuditEnumerateSchema, user=True), _d))
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "msg": "Success",
            "data": _data

        }
    )


@router.post('/audit/info')
def audit_info(
        skip: int = 0,
        limit: int = 10,
        query_sets: dict = {},
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Current user review information acquisition </br>
    :param query_sets: Information retrieval </br>
    :param skip:
    :param limit:
    :param current_user:
    :return:
    """
    skip = skip * limit
    audit_status = query_sets.get('audit_status')
    if audit_status is not None:
        query_sets.pop('audit_status')
        if audit_status is True:
            query_sets['audit_result__ne'] = "Pending review"
        else:
            query_sets['audit_result'] = "Pending review"
    if query_sets.get("content"):
        _d = AuditRecordsModel.objects(applicant=current_user.id, **query_sets).filter(
            __raw__={'content': {'$regex': f'.*{query_sets.get("content")}'}})

    else:
        _d = AuditRecordsModel.objects(applicant=current_user.id, **query_sets)
    print(query_sets)
    _d = _d.order_by('-submit_at')
    _data = list(map(lambda x: convert_mongo_document_to_schema(x, AuditRecordsSchema,
                                                                revers_map=['applicant', 'auditor', 'component']), _d))

    if query_sets.get('audit_type') is not None:
        query_sets.pop('audit_type')
    _audit_counts = [
        {"total": AuditRecordsModel.objects(audit_type=_ae.audit_type, applicant=current_user.id, **query_sets).count(),
         "audit_type": _ae.audit_type} for _ae in AuditEnumerateModel.objects.all()]

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success",
                                 "data": _data[skip: skip+limit],
                                 "counts": _audit_counts,
                                 "total": len(_data)})


@router.get('/audit/counts')
def audit_counts(
        audit_type: str = None,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Audit information classification statistics [ { "audit_type" : "Components", "total": 1}] </br>
    :param audit_type: Review Type Filter </br>
    :param current_user: Query only for the current user </br>
    :return:
    """
    if audit_type:
        _d = AuditEnumerateModel.objects(audit_type=audit_type).all()
    else:
        _d = AuditEnumerateModel.objects.all()
    _data = [{"total": AuditRecordsModel.objects(audit_type=_ae.audit_type, applicant=current_user.id).count(),
              "audit_type": _ae.audit_type} for _ae in _d]
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success",
                                 "data": _data,
                                 "total": len(_data)})


@router.get('/msg')
def get_msg(page: int = 0,
            limit: int = 10,
            current_user: UserModel = Depends(deps.get_current_user)):
    skip = page*limit
    try:
        ls = find_records(current_user.role.permissions)
        if ls:
            # msg = []
            # for _ in AuditRecordsModel.objects(audit_type__in=ls, audit_status=False).all():
            #     msg.append(_)
            # for _ in AuditRecordsModel.objects(applicant=current_user.id, audit_status=False).all():
            #     msg.append(_)

            msg = AuditRecordsModel.objects(audit_type__in=ls, audit_status=False).all()
        else:
            msg = AuditRecordsModel.objects(applicant=current_user.id, audit_status=False).all()
        _data = list(map(lambda x: convert_mongo_document_to_schema(x, AuditRecordsSchema,
                                                                    revers_map=['applicant', 'auditor', 'component']), msg))
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success",
                                     "data": _data[skip: skip+limit],
                                     "total": len(_data)
                                     }
                            )
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.get('/read/{msg_id}')
def read_msg(msg_id: str,
             current_user: UserModel = Depends(deps.get_current_user)):
    try:
        AuditRecordsModel.objects(id=msg_id).update_one(audit_status=True)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


if __name__ == '__main__':
    ...
