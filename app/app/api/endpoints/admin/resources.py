# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:resource
@time:2022/11/09
"""
import datetime
import decimal
import time
import asyncio
from fastapi import (
    APIRouter,
    Depends,
    status,
    Request
)
from fastapi.responses import JSONResponse
from typing import Optional
from app.api import deps
from app.core.config import settings
from app.models.mongo import (
    ComputingResourceAllocatedModel,
    StorageResourceAllocatedModel,
    UserQuotaStatementModel,
    ComputingQuotaRuleModel,
    ComputingResourceModel,
    StorageQuotaRuleModel,
    StorageResourceModel,
    AuditRecordsModel,
    PlatformResourceModel,
    UserQuotaModel,
    UserModel,
    QuotaResourceModel,
    QuotaStatementEnum,
    ToolTaskModel
)
from app.schemas import (
    ComputingResourceAllocatedSchema,
    StorageResourceAllocateSchema,
    UserQuotaStatementSchema,
    ComputingQuotaRuleSchema,
    ComputingResourceSchema,
    StorageQuotaRuleSchema,
    AuditRecordsSchema,
    UserQuotaSchema,
)
from app.utils.resource import platform_storage_balance_allocation
from app.utils.statement import query_statement, create_statement
from app.utils.common import convert_mongo_document_to_schema, generate_uuid
from app.utils.msg_util import creat_message
from app.utils.resource_util import get_cache_cumulative_num

router = APIRouter()
RESOURCE_TYPES = ["Computing resources", "Storage resources"]


@router.get('/storage', summary="Storage resources")
async def storage_resource(
        request: Request,
        content: str = None,
        user_role: str = None,
        page: int = 0,
        limit: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)
):
    _prm = PlatformResourceModel.objects.first()
    if _prm is None:
        _prm = PlatformResourceModel(id=generate_uuid())
        _prm.save()
    skip = page * limit
    all_users = set([_.id for _ in UserModel.objects])
    active_user = set([_.allocated_user.id for _ in StorageResourceAllocatedModel.objects])
    if len(all_users) > len(active_user):
        diff_users = all_users.difference(active_user)
    else:
        diff_users = active_user.difference(all_users)
    if diff_users:
        [StorageResourceAllocatedModel(id=generate_uuid(),
                                       user=current_user.id,
                                       allocated_storage_size=0,
                                       allocated_user=user_id).save() for user_id in diff_users]
    _data = list()
    if user_role is not None:
        _users = UserModel.objects(role=user_role)
        _d = StorageResourceAllocatedModel.objects(allocated_user__in=_users)
    elif content is not None:
        _users = UserModel.objects(name__contains=content)
        _d = StorageResourceAllocatedModel.objects(allocated_user__in=_users)
    else:
        _d = StorageResourceAllocatedModel.objects

    total_allocate = _d.sum('allocated_storage_size')
    total_allocate_use = 0

    for _ in _d:
        _size = await get_cache_cumulative_num(_.allocated_user.id, request.app.state.use_storage_cumulative)
        total_allocate_use += _size
        item = convert_mongo_document_to_schema(_, StorageResourceAllocateSchema,revers_map=['allocated_user'])
        # item['avatar'] = get_img_b64_stream(_.allocated_user.avatar).decode() if _.allocated_user.avatar is not None else None
        item['avatar'] = _.allocated_user.avatar if _.allocated_user.avatar is not None else None
        item['role'] = _.allocated_user.role.name
        item['email'] = _.allocated_user.email
        item['used_size'] = _size
        _data.append(item)

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            "data": _data[skip: skip+limit],
                            "total": len(_data),
                            "total_available": _prm.storage,
                            "total_allocate": total_allocate,
                            "total_actual_use": total_allocate_use,
                            "msg": "Success"
                        })


@router.post('/storage', summary="Storage resourcesallocation")
def storage_resource_create(
        user_id: str,
        allocated_storage_size: int,
        current_user: UserModel = Depends(deps.get_current_user)
):
    if platform_storage_balance_allocation(allocated_storage_size):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Storage resources,Unable to allocate！"})
    StorageResourceAllocatedModel(id=generate_uuid(),
                                  user=current_user.id,
                                  allocated_storage_size=allocated_storage_size,
                                  allocated_user=user_id).save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"})


@router.post('/storage/allocated/role', summary="Storage resources, allocationRoleStorage resources")
def storage_allocated_creat(
        role_id: str,
        allocated_storage_size: int,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Storage resourcesallocationRole </br>
    :param role_id: Roleid</br>
    :param allocated_storage_size: Authorized usage of resources</br>
    :return:
    """
    _users = UserModel.objects(role=role_id)
    if len(_users) < 1:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Role!"})
    if platform_storage_balance_allocation(len(_users)*allocated_storage_size):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "The remaining storage is insufficient for batch allocation"})
    for _ in _users:
        allocated_storage = StorageResourceAllocatedModel.objects(allocated_user=_).first()
        if allocated_storage:
            new_allocated_storage_size = allocated_storage_size+allocated_storage.allocated_storage
            allocated_storage.update(allocated_storage_size=new_allocated_storage_size)
        else:
            StorageResourceAllocatedModel(id=generate_uuid(),
                                          user=current_user.id,
                                          allocated_storage_size=allocated_storage_size,
                                          allocated_user=_).save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"})


@router.put('/storage', summary="Storage resources")
def storage_resource_update(
        storage_id: str,
        allocated_storage_size: int,
        current_user: UserModel = Depends(deps.get_current_user)):
    try:
        StorageResourceAllocatedModel.objects(id=storage_id).\
            update_one(allocated_storage_size=allocated_storage_size,
                       last_update_time=datetime.datetime.utcnow(),
                       )

        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"Resource exception: {e}"})


@router.post('/storage/newcomer', summary="New users are assigned storage Settings by default")
async def set_newcomer_storage(allocated_storage_size: int,
                               current_user: UserModel = Depends(deps.get_current_user)
                               ):
    try:
        StorageResourceModel.objects.first().update(newcomer=allocated_storage_size)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"allocationStorage resources: {e}"})


@router.get('/storage/newcomer', summary="Gets the default allocated storage for the current new user")
async def get_newcomer_storage(
                               current_user: UserModel = Depends(deps.get_current_user)
                               ):
    try:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!",
                                     "data": StorageResourceModel.objects.first().newcomer})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"allocationStorage resources: {e}"})


@router.post('/quota/newcomer', summary="Default quota setting for new users")
async def set_newcomer_quota(allocated_storage_size: int,
                               current_user: UserModel = Depends(deps.get_current_user)
                               ):
    try:
        QuotaResourceModel.objects.first().update(newcomer=allocated_storage_size)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!"})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"allocationStorage resources: {e}"})


@router.get('/quota/newcomer', summary="Gets the default quota allocated for the current new user")
async def get_newcomer_storage(
                               current_user: UserModel = Depends(deps.get_current_user)
                               ):
    try:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!",
                                     "data": QuotaResourceModel.objects.first().newcomer})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Failed to obtain the default allocated quota for a new user: {e}"})


@router.get('/computing_quota', summary="Computing resources")
async def get_computing_quota(current_user: UserModel = Depends(deps.get_current_user)):
    _computing_quota = ComputingQuotaRuleModel.objects.first()
    if _computing_quota is None:
        _computing_quota = ComputingQuotaRuleModel(id=generate_uuid(),
                                                   user=current_user
                                                   ).save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": convert_mongo_document_to_schema(_computing_quota, ComputingQuotaRuleSchema),
                                 "msg": "Successful!"}
                        )


@router.post('/computing_quota', summary="Computing resources")
async def update_computing_quota(cpu_quota: Optional[float] = None,
                                 cpu_unit_measurement: Optional[str] = None,
                                 memory_quota: Optional[float] = None,
                                 memory_unit_measurement: Optional[str] = None,
                                 gpu_quota: Optional[float] = None,
                                 gpu_unit_measurement: Optional[str] = None,
                                 current_user: UserModel = Depends(deps.get_current_user)):
    _update = {"cpu_quota": cpu_quota, "cpu_unit_measurement": cpu_unit_measurement,
               "memory_quota": memory_quota, "memory_unit_measurement": memory_unit_measurement, "gpu_quota": gpu_quota,
               "gpu_unit_measurement": gpu_unit_measurement}
    _update = {k: v for k, v in _update.items() if v is not None}
    if _update:
        _update['update_at'] = datetime.datetime.utcnow()
        ComputingQuotaRuleModel.objects.first().update(**_update)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            "msg": "Successful!"}
                        )


@router.get('/storage_quota', summary="Get the quota conversion storage rule")
async def get_storage_quota(current_user: UserModel = Depends(deps.get_current_user)):
    storage_quota_rule = StorageQuotaRuleModel.objects.first()
    if storage_quota_rule is None:
        storage_quota_rule = StorageQuotaRuleModel(id=generate_uuid(),
                                                   user=current_user
                                                   ).save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": convert_mongo_document_to_schema(storage_quota_rule, StorageQuotaRuleSchema),
                                 "msg": "Successful!"}
                        )


@router.post('/storage_quota', summary="Modify the quota conversion storage rule")
async def update_storage_quota(quota: Optional[int] = None,
                               storage_unit_measurement: Optional[str] = None,
                               enable: Optional[bool] = None,
                               current_user: UserModel = Depends(deps.get_current_user)):
    _update = {"storage_quota": quota, "enable": enable, "storage_unit_measurement": storage_unit_measurement}
    _update = {k: v for k, v in _update.items() if v is not None}
    if _update:
        _update['update_at'] = datetime.datetime.utcnow()
        StorageQuotaRuleModel.objects.first().update(**_update)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                                 "msg": "Successful!"}
                        )


@router.post('/quota', summary="Quota flow details")
async def quota_statement(request:Request,
                          statement_id: Optional[str] = None,
                          user: Optional[str] = None,
                          email: Optional[str] = None,
                          organization: Optional[str] = None,
                          statement_type: Optional[str] = None,
                          begin_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          order_by: Optional[str] = None,
                          page: Optional[int] = 0,
                          limit: Optional[int] = 10,
                          current_user: UserModel = Depends(deps.get_current_user)):
    skip = page * limit
    statement_list, total = await query_statement(statement_id=statement_id,
                                                  user=user, email=email,
                                                  organization=organization,
                                                  statement_type=statement_type, begin_time=begin_time,
                                                  end_time=end_time, order_by=order_by, skip=skip, limit=limit,request=request)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": statement_list,
                                 "total": total,
                                 "msg": "Successful!"})


@router.post('/init_storage')
async def init_platform_resource(current_user: UserModel = Depends(deps.get_current_user)):
    StorageResourceModel(id=generate_uuid(), allocated_user=current_user,
                         last_update_user=current_user).save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.post('/init_quota')
async def init_platform_quota(current_user: UserModel = Depends(deps.get_current_user)):
    _quota_entity = QuotaResourceModel.objects().first()
    if _quota_entity is None:
        QuotaResourceModel(id=generate_uuid(),
                           allocated_user=current_user,
                           last_update_user=current_user

                           ).save()
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Quota initialization"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": f"Quotas do not need to initialize the current default quota:{_quota_entity.newcomer}"})


@router.get('/jsj')
async def create_fake_data(current_user: UserModel = Depends(deps.get_current_user)):
    for task in ToolTaskModel.objects[:3]:
        UserQuotaStatementModel(id=generate_uuid(), original_balance=201,  balance=201, statement_type="Tasks", occurrence_time=datetime.datetime.utcnow(),use=100, user=current_user, operator=current_user, event=task).save()
    return {}


@router.get('/quota/users')
async def search_users_quota(name: Optional[str] = None,
                             page: int = 0,
                             size: int = 10,
                             current_user: UserModel = Depends(deps.get_current_user)):
    skip = page * size
    if name is not None:
        users_id = [_.id for _ in UserModel.objects(name__contains=name).all()]
        users_quota = UserQuotaModel.objects(user__in=users_id)
        _data = list(map(lambda x: convert_mongo_document_to_schema(x, UserQuotaSchema, user=True),
                         UserQuotaModel.objects(user__in=users_id))
                     )
    else:
        users_quota = UserQuotaModel.objects
    _data = list()
    for _ in users_quota:
        item = convert_mongo_document_to_schema(_, UserQuotaSchema, user=True)
        item['user_id'] = _.user.id
        item['used_quota'] = abs(UserQuotaStatementModel.objects(user=_.user, statement_type__ne="allocation").sum('use'))
        item['quota'] = _.balance
        _data.append(item)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "total": len(_data),
                                 "data": _data[skip: skip+size]})


@router.post('/quota/allocation/role', summary="Roleallocation")
async def allocation_quota_by_role(role_id: str,
                                   quota: Optional[float] = None,
                                   reset: Optional[float] = None,
                                   remark: Optional[str] = None,
                                   current_user: UserModel = Depends(deps.get_current_user)):
    if reset is None and quota is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "allocation"})
    if reset and quota:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Repeat typing"})
    _users = UserModel.objects(role=role_id)
    if len(_users) < 1:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Role!"})
    _statement_task = list()
    for _ in _users:
        _user_quota = UserQuotaModel.objects(user=_).first()
        if _user_quota:
            if quota:
                new_quota = quota + _user_quota.quota
                new_balance = quota + _user_quota.balance
            else:
                new_quota = reset
                new_balance = reset
            _user_quota.update(quota=new_quota, balance=new_balance)
            _statement_task.append(asyncio.create_task(create_statement(new_balance,
                                                                           _user_quota.quota,
                                                                           _,
                                                                           current_user,
                                                                           QuotaStatementEnum.allocation, remark)))
        else:
            newcomer_quota = QuotaResourceModel.objects.first().newcomer + quota
            UserQuotaModel(id=generate_uuid(),
                           user=_,
                           quota=newcomer_quota,
                           balance=newcomer_quota
                           ).save()
            _statement_task.append(asyncio.create_task(create_statement(newcomer_quota,
                                                                                      0,
                                                                                      _,
                                                                                      current_user,
                                                                                      QuotaStatementEnum.allocation, remark)))
    await asyncio.wait(_statement_task)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"})


@router.post('/quota/allocation/user', summary="allocation")
async def allocation_quota_by_user(users: list,
                                   quota: Optional[float] = None,
                                   reset: Optional[float] = None,
                                   remark: Optional[str] = None,
                                   current_user: UserModel = Depends(deps.get_current_user)):
    if reset is None and quota is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "allocation"})
    if reset and quota:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Repeat typing"})
    _users = UserModel.objects(id__in=users)
    _statement_task = list()
    for _ in _users:
        _user_quota = UserQuotaModel.objects(user=_).first()
        if _user_quota:
            if quota:
                quota = decimal.Decimal(quota)
                new_quota = quota + decimal.Decimal(_user_quota.quota)
                new_balance = quota + decimal.Decimal(_user_quota.balance)
            else:
                reset = decimal.Decimal(reset)
                new_quota = reset
                new_balance = reset
            _user_quota.update(quota=float(new_quota), balance=float(new_balance))
            _statement_task.append(asyncio.create_task(create_statement(new_balance,
                                                                        _user_quota.quota,
                                                                        _,
                                                                        current_user,
                                                                        QuotaStatementEnum.allocation,
                                                                        remark)))
        else:
            newcomer_quota = QuotaResourceModel.objects.first().newcomer + quota
            UserQuotaModel(id=generate_uuid(),
                           user=_,
                           quota=newcomer_quota,
                           balance=newcomer_quota).save()
            _statement_task.append(asyncio.create_task(create_statement(newcomer_quota,
                                                                                      0,
                                                                                      _,
                                                                                      current_user,
                                                                                      QuotaStatementEnum.allocation,
                                                                        remark)))
    await asyncio.wait(_statement_task)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"})


# @router.delete('/storage', summary="allocationStorage resources")
# def storage_resource_delete(storage_id: str,
#                             current_user: UserModel = Depends(deps.get_current_user)):
#     StorageResourceAllocatedModel.objects(id=storage_id).first().delete()
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Successful!"})
#
#
# @router.get('/computing', summary="Computing resources， Computing resources")
# def computing_resource(
#         page: int = 0,
#         limit: int = 10,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     skip = page * limit
#     _d = ComputingResourceModel.objects
#     _data = list(map(lambda x: convert_mongo_document_to_schema(x, ComputingResourceSchema,
#                                                                 revers_map=['allocated_user', "allocated_time",
#                                                                             "last_update_user"]), _d))
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={
#                             "data": _data[skip: skip+limit],
#                             "total": len(_data),
#                             "msg": "Success"
#                         })
#
#
# @router.post('/computing', summary="Computing resources， Computing resources")
# def computing_resource_create(
#         name: str,
#         core: str,
#         core_nums: int,
#         memory_nums: int,
#         description: str = "",
#         apply: bool = True,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     ComputingResourceModel(id=generate_uuid(),
#                            name=name,
#                            allocated_user=current_user.id,
#                            computing_core=core,
#                            description=description,
#                            apply=apply,
#                            core_nums=core_nums,
#                            memory_nums=memory_nums,
#                            last_update_user=current_user.id,
#                            ).save()
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
#
#
# @router.put('/computing', summary="Computing resources， Computing resources")
# def computing_resource_update(
#         resource_id: str,
#         name: str = None,
#         description: str = None,
#         apply: bool = None,
#         core_nums: int = None,
#         memory_nums: int = None,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     _params = {"name": name, "description": description, "apply": apply, "last_update_time": datetime.datetime.utcnow(),
#                "core_nums": core_nums, "memory_nums": memory_nums, "last_update_user": current_user}
#     print({k: v for k, v in _params.items() if v is not None})
#     ComputingResourceModel.objects(id=resource_id).update_one(**{k: v for k, v in _params.items() if v is not None})
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
#
#
# @router.delete('/computing', summary="Computing resources， Computing resources")
# def computing_resource_delete(
#         resource_id: str,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     ComputingResourceModel.objects(id=resource_id).first().delete()
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
#
#
# @router.get('/computing/allocated', summary="Computing resources, allocationComputing resources")
# def computing_allocated(
#         base_id,
#         page: int = 0,
#         limit: int = 10,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     skip = page*limit
#     _d = ComputingResourceAllocatedModel.objects(computing_resource_base=base_id).all()
#     _data = list(map(lambda x: convert_mongo_document_to_schema(x, ComputingResourceAllocatedSchema,
#                                                                 revers_map=['allocated_user', "allocated_time",
#                                                                             "last_update_user", "user"
#                                                                             ]), _d))
#     ls = list()
#     time_now = time.mktime(datetime.datetime.utcnow().timetuple())
#     for _ in _d:
#         item = convert_mongo_document_to_schema(_, ComputingResourceAllocatedSchema,
#                                          revers_map=['allocated_user', "allocated_time",
#                                                      "last_update_user", "user"
#                                                      ])
#         _allocated_time_smtp = time.mktime(_.allocated_time.timetuple())
#         consuming = time_now - _allocated_time_smtp
#         remaining = _.allocated_use_time - consuming
#         item['remaining'] = remaining if remaining > 0 else 0
#         ls.append(item)
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={
#                             "data": ls[skip: skip+limit],
#                             "total": len(ls),
#                             "msg": "Success"
#                         })
#
#
# @router.post('/computing/allocated', summary="Computing resources, allocationComputing resources")
# def computing_allocated_creat(
#         user: list,
#         base_id: str,
#         allocated_use_time: int,
#         current_user: UserModel = Depends(deps.get_current_user)):
#     """
#     Computing resourcesallocation </br>
#     :param user: Specifies the user to obtain the resourceid</br>
#     :param base_id: Computing resourcesid</br>
#     :param allocated_use_time: Authorized use time In seconds</br>
#     :return:
#     """
#     for _ in user:
#         ComputingResourceAllocatedModel(id=generate_uuid(),
#                                         user=current_user.id,
#                                         computing_resource_base=base_id,
#                                         allocated_user=_,
#                                         allocated_use_time=allocated_use_time,
#                                         ).save()
#     counts = ComputingResourceAllocatedModel.objects(computing_resource_base=base_id).count()
#     ComputingResourceModel.objects(id=base_id).update_one(user_count=counts)
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
#
#
# @router.post('/computing/allocated/role', summary="Computing resources, allocationRoleComputing resources")
# def computing_allocated_creat(
#         role_id: str,
#         base_id: str,
#         allocated_use_time: int,
#         current_user: UserModel = Depends(deps.get_current_user)):
#     """
#     Computing resourcesallocation </br>
#     :param user: Specifies the user to obtain the resourceid</br>
#     :param base_id: Computing resourcesid</br>
#     :param allocated_use_time: Authorized use time In seconds</br>
#     :return:
#     """
#     _users = UserModel.objects(role=role_id)
#     for _ in _users:
#         ComputingResourceAllocatedModel(id=generate_uuid(),
#                                         user=current_user.id,
#                                         computing_resource_base=base_id,
#                                         allocated_user=_,
#                                         allocated_use_time=allocated_use_time,
#                                         ).save()
#     counts = ComputingResourceAllocatedModel.objects(computing_resource_base=base_id).count()
#     ComputingResourceModel.objects(id=base_id).update_one(user_count=counts)
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
#
#
# @router.post('/computing/allocated/all', summary="Computing resources, allocationComputing resources")
# def computing_allocated_creat(
#         base_id: str,
#         allocated_use_time: int,
#         current_user: UserModel = Depends(deps.get_current_user)):
#     """
#     Computing resourcesallocation </br>
#     :param user: Specifies the user to obtain the resourceid</br>
#     :param base_id: Computing resourcesid</br>
#     :param allocated_use_time: Authorized use time In seconds</br>
#     :return:
#     """
#     _users = UserModel.objects()
#     for _ in _users:
#         ComputingResourceAllocatedModel(id=generate_uuid(),
#                                         user=current_user.id,
#                                         computing_resource_base=base_id,
#                                         allocated_user=_,
#                                         allocated_use_time=allocated_use_time,
#                                         ).save()
#     counts = ComputingResourceAllocatedModel.objects(computing_resource_base=base_id).count()
#     ComputingResourceModel.objects(id=base_id).update_one(user_count=counts)
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
#
#
# @router.put('/computing/allocated', summary="Computing resources, allocationComputing resources")
# def computing_allocated_creat(
#         resource_id: str,
#         allocated_use_time: int,
#         current_user: UserModel = Depends(deps.get_current_user)):
#     ComputingResourceAllocatedModel.objects(id=resource_id).update_one(allocated_use_time=allocated_use_time,
#                                                                        user=current_user,
#                                                                        last_update_time=datetime.datetime.utcnow())
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
#
#
# @router.delete('/computing/allocated', summary="Computing resources, Computing resources")
# def computing_allocated_delete(
#         resource_id: str,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#     _d = ComputingResourceAllocatedModel.objects(id=resource_id).first()
#     counts = ComputingResourceAllocatedModel.objects(computing_resource_base=_d.computing_resource_base.id).count()
#     ComputingResourceModel.objects(id=_d.computing_resource_base.id).update_one(user_count=counts)
#     _d.delete()
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})


# @router.get('/audit')
# async def resource_audit(request: Request,
#                          page: int= 0,
#                          limit: int=10,
#                          name: str = None,
#                          audit_result: str = None,
#                          audit_type: str = None,
#                          current_user: UserModel = Depends(deps.get_current_user)):
#
#     query ={k: v  for k,v in  {'content__contains': name, "audit_result": audit_result, "audit_type": audit_type}.items()
#             if v is not None}
#     if query:
#         _d = AuditRecordsModel.objects(audit_type__in=RESOURCE_TYPES, **query)
#     else:
#         _d = AuditRecordsModel.objects(audit_type__in=RESOURCE_TYPES)
#     storage_nums = 0
#     computing_nums = 0
#     for _ in _d:
#         if _.audit_type=="Computing resources":
#             storage_nums+=1
#         else:
#             computing_nums +=1
#     skip = page*limit
#     resource_audit_data = list()
#     for _ in _d:
#         item = convert_mongo_document_to_schema(_, AuditRecordsSchema,revers_map=['applicant', 'auditor', 'component'])
#         try:
#             # item['avatar'] = get_img_b64_stream(_.applicant.avatar).decode() if _.applicant.avatar is not None else None
#             item['avatar'] = _.applicant.avatar if _.applicant.avatar is not None else None
#         except:
#             item['avatar'] = None
#         try:
#             item['email'] = _.applicant.email
#         except :
#             item['email'] = None
#         if _.audit_type == "Storage resources":
#             item["used"] = await get_cache_cumulative_num(_.applicant.id, request.app.state.use_storage_cumulative)
#             item['total_size'] = StorageResourceAllocatedModel.objects(
#                 allocated_user=_.applicant.id).first().allocated_storage_size
#             item['remain'] = item['total_size'] - item['used']
#         resource_audit_data.append(item)
#     # resource_audit_data = \
#     #     list(map(lambda x: convert_mongo_document_to_schema( x, AuditRecordsSchema),
#     #         _d))
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"data": resource_audit_data[skip: skip+limit],
#                                  "total": len(resource_audit_data),
#                                  "storage_nums": storage_nums,
#                                  "computing_nums": computing_nums})
#

# @router.put('/audit/storage/{resource_id}',
#             summary="Storage resources")
# def audit_computing(resource_id: str,
#           audit: str,
#           info: str = '',
#             size: int = None,
#           current_user: UserModel = Depends(deps.get_current_user)
#                      ):
#     try:
#         if audit not in settings.AUDIT_ALLOW:
#             return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
#                                 content={"msg": "Malicious approval"})
#         ar = AuditRecordsModel.objects(id=resource_id).first()
#         if audit == "Approved by review":
#             _resources = ar.component
#             _cra = StorageResourceAllocatedModel.objects(id=generate_uuid(),
#                                                  user=current_user,
#                                                  allocated_user=ar.applicant,
#                                                 allocated_storage_size=ar.apply_nums if size is None else size,
#                                                    )
#
#             _cra.save()
#         AuditRecordsModel.objects(id=resource_id).update_one(audit_result=audit,
#                                                              audit_at=datetime.datetime.utcnow(),
#                                                              auditor=current_user,
#                                                              audit_info=info
#                                                                  )
#         ar = AuditRecordsModel.objects(id=resource_id).first()
#         creat_message(user=ar.applicant, message_base=ar,for_user=True)
#         return JSONResponse(status_code=status.HTTP_200_OK,
#                             content={"msg": "Success"})
#
#     except Exception as e:
#         return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
#                             content={"msg": str(e)})
#
#
# @router.put('/audit/computing/{resource_id}',
#             summary="Computing resources")
# def audit_storage(resource_id: str,
#           audit: str,
#           info: str = '',
#           size: int = None,
#           current_user: UserModel = Depends(deps.get_current_user)
#                      ):
#     "size"
#     try:
#         if audit not in settings.AUDIT_ALLOW:
#             return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
#                                 content={"msg": "Malicious approval"})
#         ar = AuditRecordsModel.objects(id=resource_id).first()
#         if audit == "Approved by review":
#             _resources = ar.component
#             _cra = ComputingResourceAllocatedModel(id=generate_uuid(),
#                                                    user=current_user.id,
#                                                    computing_resource_base=_resources.id,
#                                                    allocated_user=ar.applicant,
#                                                    allocated_use_time=ar.apply_nums if size is None else size,
#                                                    )
#             _cra.save()
#             # print(_cra)
#             counts = ComputingResourceAllocatedModel.objects(computing_resource_base=_resources.id).count()
#             ComputingResourceModel.objects(id=_resources.id).update_one(user_count=counts)
#         AuditRecordsModel.objects(id=resource_id).update_one(audit_result=audit,
#                                                              audit_info=info,
#                                                              audit_at=datetime.datetime.utcnow(),
#                                                              auditor=current_user
#                                                                  )
#         ar = AuditRecordsModel.objects(id=resource_id).first()
#         creat_message(user=ar.applicant, message_base=ar, for_user=True)
#         return JSONResponse(status_code=status.HTTP_200_OK,
#                             content={"msg": "Success"})
#
#     except Exception as e:
#         return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
#                             content={"msg": str(e)})


