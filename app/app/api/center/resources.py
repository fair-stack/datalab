# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:resources
@time:2022/11/09
"""
import time
import copy
from typing import Optional
from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    status,
    Request
)
from fastapi.responses import JSONResponse
from app.api import deps
from app.utils.msg_util import creat_message
from app.utils.resource_util import get_cache_cumulative_num
from app.utils.statement import query_statement, create_statement
from app.utils.common import convert_mongo_document_to_schema, generate_uuid
from app.models.mongo import (
    UserModel,
    ToolTaskModel,
    UserQuotaModel,
    SkeletonModel2,
    AnalysisModel2,
    DataFileSystem,
    ExperimentModel,
    ComponentInstance,
    AuditRecordsModel,
    XmlToolSourceModel,
    QuotaStatementEnum,
    StorageResourceModel,
    NoteBookProjectsModel,
    StorageQuotaRuleModel,
    ComputingResourceModel,
    UserQuotaStatementModel,
    StorageResourceAllocatedModel,
    ComputingResourceAllocatedModel,
)
from app.schemas import (
    DatasetV2Schema,
    ComputingResourceSchema,
    StorageResourceAllocateSchema,
    ComputingResourceAllocatedSchema,
    ComputingResourceAllocatedResponseSchema,
    )
router = APIRouter()


@router.get('/computing', summary="Personal Center-List of computing resources")
def computing_resources(
        page: int = 0,
        limit: int = 10,
        resource_type: str = None,
        current_user: UserModel = Depends(deps.get_current_user)
):
    skip = page * limit
    if resource_type:
        _d = ComputingResourceModel.objects(computing_core=resource_type)
        _allocated = ComputingResourceAllocatedModel.objects(allocated_user=current_user.id,
                                                             computing_resource_base__in=_d)
    else:
        _d = ComputingResourceModel.objects()
        _allocated = ComputingResourceAllocatedModel.objects(allocated_user=current_user.id)
    _data = {i['id']: i for i in map(lambda x: convert_mongo_document_to_schema(x, ComputingResourceSchema,
                                                                                revers_map=['allocated_user',
                                                                                            "allocated_time",
                                                                                            "last_update_user"]), _d)}
    print(_data)
    time_now = time.mktime(datetime.utcnow().timetuple())
    ls = list()
    used_resources = set()
    for _ in _allocated:
        _allocated_time_smtp = time.mktime(_.allocated_time.timetuple())
        consuming = time_now - _allocated_time_smtp
        _item = convert_mongo_document_to_schema(_, ComputingResourceAllocatedSchema,
                                                 revers_map=['allocated_user'])
        print(_item['computing_resource_base'])
        base_resource = copy.deepcopy(_data.get(_item['computing_resource_base']))
        used_resources.add(_item['computing_resource_base'])
        base_resource.update(_item)
        base_resource['consuming'] = consuming
        remaining = _.allocated_use_time - consuming
        base_resource['remaining'] = remaining if remaining >0 else 0
        ls.append(base_resource)
    resources = list()
    response_content = dict()
    response_content['resources_count'] = list()
    _resources_count_map = dict()
    for _ in _data.values():
        if _['id'] not in used_resources:
            resources.append(_)
        if _resources_count_map.get(_['computing_core']) is None:
            _resources_count_map[_['computing_core']] = 0
        _resources_count_map[_['computing_core']] = _resources_count_map[_['computing_core']] +1
    response_content['resources_count'] = [{"name": k, "value": v} for k, v in _resources_count_map.items()]
    response_content['data'] = ls[skip: skip+limit]
    response_content["resources"] = resources
    response_content["total"] = len(_data) + len(resources)
    response_content["msg"] = "Success"
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=response_content)


@router.post('/apply/computing', summary="Personal Center-Computing resource request")
def apply_computing_resources(resource_id: str,
                              allocated_use_time: int,
                              content: str,
                              current_user: UserModel = Depends(deps.get_current_user)
                              ):
    """
    Allocate existing computing resources to a user </br>
    :param content: Application Information</br>
    :param resource_id: Computing resourcesid</br>
    :param allocated_use_time: Application time In seconds</br>
    :return:
    """
    try:
        applicant = current_user
        audit_records = AuditRecordsModel(id=generate_uuid(),
                                          applicant=applicant,
                                          content=content,
                                          audit_result="Pending review",
                                          component=ComputingResourceModel.objects(id=resource_id).first(),
                                          audit_type="Computing resources",
                                          apply_nums=allocated_use_time,
                                          )
        audit_records.save()
        creat_message(user=current_user, message_base=audit_records)
        return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Computing resource request!"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.post('/apply/storage', summary="Personal Center-Storage resource request")
def apply_computing_resources(
                              allocated_use: int,
                              content: str,
                              current_user: UserModel = Depends(deps.get_current_user)
                              ):
    """
    Allocate existing computing resources to a user </br>
    :param content: Application Information</br>
    :param allocated_use: The unit of the requested storage usage isBytes</br>
    :return:
    """
    try:
        applicant = current_user
        audit_records = AuditRecordsModel(id=generate_uuid(),
                                          applicant=applicant,
                                          content=content,
                                          audit_result="Pending review",
                                          audit_type="Storage resources",
                                          apply_nums=allocated_use,
                                          )
        audit_records.save()
        creat_message(user=current_user, message_base=audit_records)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Storage resource request!"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.post('/statement', summary="Personal Centerquota")
async def quota_statement(request: Request,
                          statement_id: Optional[str] = None,
                          begin_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          order_by: Optional[str] = None,
                          page: Optional[int] = 0,
                          limit: Optional[int] = 10,
                          current_user: UserModel = Depends(deps.get_current_user)):
    skip = page*limit
    statement_list, total = await query_statement(
        statement_id=statement_id, user_id=current_user.id,
        begin_time=begin_time, end_time=end_time, order_by=order_by,
        skip=skip, limit=limit, request=request)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": statement_list,
                                 "total": total,
                                 "msg": "Successful!"})


@router.get('/balance', summary="My balance")
async def get_my_balance(current_user: UserModel = Depends(deps.get_current_user)):
    _my_balance = UserQuotaModel.objects(user=current_user).first().balance
    # if _my_balance > 999999999:
    #     _my_balance = "infinite"
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _my_balance,
                                 "msg": "Successful!"})


@router.get('/data', summary="My Data")
async def get_my_data_storage_size(request: Request,
                                   current_user: UserModel = Depends(deps.get_current_user)):
    data_total = await get_cache_cumulative_num(current_user.id, request.app.state.use_storage_cumulative)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": data_total,
                                 "msg": "Successful!"})


@router.get('/recently', summary="Recently used analysis/Experiment")
async def recently_used(current_user: UserModel = Depends(deps.get_current_user)):
    # Force four Experiment，Two analyses
    all_recently = list()
    all_recently.extend(ExperimentModel.objects(user=current_user).order_by('-created_at').limit(1))
    all_recently.extend(AnalysisModel2.objects(user=current_user).order_by('-created_at').limit(1))
    _data = list()
    for _recently in all_recently:
        try:
            item = dict()
            item['id'] = _recently.id
            item['name'] = _recently.name
            item['created_at'] = _recently.created_at.strftime('%Y/%m/%d %H:%M:%S')
            item['updated_at'] = _recently.updated_at.strftime('%Y/%m/%d %H:%M:%S')
            if isinstance(_recently, AnalysisModel2):
                item['id'] = _recently.skeleton.id
                item['type'] = "analysis"
                item['description'] = _recently.skeleton.description
                item['logo'] = _recently.skeleton.logo
                item['name'] = _recently.skeleton.name
            else:
                item['description'] = _recently.description
                item['type'] = "experiments"
            _data.append(item)
        except Exception as e:
            pass
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "data": _data
                                 })


@router.get('/recently_data', summary="Recent Achievements")
async def recently_data(current_user: UserModel = Depends(deps.get_current_user)):
    """
    Recent results<file/Objects> <br>
    :return: {"data": [{"id": "", "type": "file/object", "format", "name": "Name"}]}
    """
    _d = DataFileSystem.objects(user=current_user, data_type="TaskData").order_by("-created_at")
    _count = 0
    data = list()
    for _t in _d:
        _ = convert_mongo_document_to_schema(_t, DatasetV2Schema, user=True, revers_map=['user'])
        try:
            _task = ToolTaskModel.objects(id=_t.task_id).first()
            if _task:
                _from = f"Experiment<{_task.experiment.name}>the{_task.name}"
            else:
                _task = AnalysisModel2.objects(id=_t.lab_id).first()
                _from = f"Analysis tools{_task.skeleton.name}<{_task.name}>the"
            _['from_source'] = _from
            _['_from'] = "COMPUTING" if _['data_type'] == "TaskData" else "UPLOAD"
            data.append(_)
            _count += 1
        except:
            pass
        if _count == 10:
            break
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "data": data})


@router.get('/overview', summary="Overview Statistics<thetheExperimentthe>")
async def overview_total(current_user: UserModel = Depends(deps.get_current_user)):
    """
    Overview Statistics<thetheExperimentthe> <br>
    :return:{"experiments_count": "Experiment", "analysis_count": "Number of analyses"，"project_count": "Number of online programming projects"}
    """
    experiments_count = ExperimentModel.objects(user=current_user, is_shared=False, is_trial=False).count()
    analysis_count = AnalysisModel2.objects(user=current_user).count()
    projects_oep = NoteBookProjectsModel.objects(user=current_user).count()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "experiments_count": experiments_count,
                                 "analysis_count": analysis_count,
                                 "project_count": projects_oep})


@router.get('/tools', summary="the")
async def my_tools_info(current_user: UserModel = Depends(deps.get_current_user)):
    """
    Personal Center，<the> <br>
    :return:{"data": {"draft": "the", "under_review": "the"，"audited": "the"}}
    """
    _group = XmlToolSourceModel.objects(user=current_user).aggregate(
        [
            {'$group': {"_id": "$audit", "sum": {"$sum": 1}}}
        ])
    draft = 0
    under_review = 0
    audited = 0
    for i in _group:
        if i['_id'] == "Failed to pass the audit" or i['_id'] == "Approved by review":
            audited += i['sum']
        elif i['_id'] == "Not committed":
            draft += i['sum']
        else:
            under_review += i['sum']

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!", "draft": draft, "under_review": under_review,
                                 "audited": audited})


@router.get('/skeleton', summary="the")
async def my_publish_skeletons(current_user: UserModel = Depends(deps.get_current_user)):
    """
    Personal Center，<the> <br>
    :return:{"data": {"draft": "the", "under_review": "the"，"audited": "the"}}
    """
    _group = SkeletonModel2.objects(user=current_user).aggregate(
        [
            {'$group': {"_id": "$state", "sum": {"$sum": 1}}}
        ])
    "UNAPPROVED"
    draft = 0
    under_review = 0
    audited = 0
    for i in _group:
        if i['_id'] == "DISAPPROVED" or i['_id'] == "APPROVED":
            audited += i['sum']
        elif i['_id'] == "UNAPPROVED":
            draft += i['sum']
        else:
            under_review += i['sum']
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!", "draft": draft, "under_review": under_review,
                                 "audited": audited})


@router.post('/exchange/storage', summary="Use quota to redeem storage")
async def exchange_storage(storage_size: float,
                           current_user: UserModel = Depends(deps.get_current_user)):
    _quota_rule = StorageQuotaRuleModel.objects.first()
    unit_map = {
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4
                }
    try:
        if _quota_rule is not None:
            _exchange_value = _quota_rule.storage_quota
            user_quota = UserQuotaModel.objects(user=current_user).first()
            _need_quota = _exchange_value*storage_size
            original_balance = user_quota.balance
            if _need_quota <= user_quota.balance:
                print(user_quota)
                user_quota.update(balance=original_balance-_need_quota)
                _balance = original_balance-_need_quota
                _storage_resource = StorageResourceAllocatedModel.objects(user=current_user).first()
                print(_storage_resource)
                _storage_resource.update(
                    allocated_storage_size=_storage_resource.allocated_storage_size+storage_size*unit_map[
                        _quota_rule.storage_unit_measurement])
                await create_statement(_balance, original_balance, current_user, current_user,
                                       QuotaStatementEnum.storage_exchange)
                return JSONResponse(status_code=status.HTTP_200_OK,
                                    content={"msg": "Successful!"}
                                    )
            else:
                nee_some_storage = f"{storage_size}/{_quota_rule.storage_unit_measurement}"
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"The current balance is not sufficient for conversion{nee_some_storage}theStorage resources,To exchange this amount of resources{_need_quota}quota！"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Exchange failure，{e}!"})

