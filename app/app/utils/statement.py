# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:statement
@time:2023/03/06
"""
import json
from fastapi import Request
from datetime import datetime
from typing import Optional
from mongoengine.errors import DoesNotExist
from app.models.mongo import (UserQuotaModel,
                              StorageQuotaRuleModel,
                              ComputingQuotaRuleModel,
                              UserQuotaStatementModel,
                              QuotaStatementEnum,
                              ExperimentModel,
                              ToolTaskModel,
                              UserModel)
from app.schemas import (StorageQuotaRuleSchema,
                         UserQuotaSchema,
                         UserQuotaStatementSchema,
                         ComputingQuotaRuleSchema)
from app.utils.common import generate_uuid


async def query_task(events, request=None):
    item = dict()
    item['start_time'] = events.created_at.strftime('%Y/%m/%d %H:%M:%S')
    item['end_time'] = events.updated_at.strftime('%Y/%m/%d %H:%M:%S')
    item['experiment'] = events.experiment.name
    item['name'] = events.name
    item['task_id'] = events.id
    item['use_time'] = (events.updated_at - events.created_at).total_seconds()
    item['cpu'] = 0
    item['memory'] = 0
    return item


async def query_analysis(events, request):
    all_task = json.loads(await request.app.state.task_publisher.get(events.id+"-stage"))
    print(all_task)
    all_cpu_use = 0
    all_memory_use = 0
    for _ in all_task:
        result_use_resource = await request.app.state.task_publisher.get(f"{_}-resource")
        if result_use_resource is None:
            cpu_used = 1
            memory_used = 1
        else:
            result_use_resource = json.loads(result_use_resource)
            cpu_used = sum([_ for _ in result_use_resource['cpu_used_list']])
            memory_used = sum([_ for _ in result_use_resource['memory_percent_list']])
        all_cpu_use += cpu_used
        all_memory_use += memory_used
    item = {
        "start_time": events.created_at.strftime('%Y/%m/%d %H:%M:%S'),
        "end_time": events.updated_at.strftime('%Y/%m/%d %H:%M:%S'),
        "analysis": events.name,
        "analysis_id": events.id,
        "source": events.skeleton.name,
        "use_time": (events.updated_at - events.created_at).total_seconds(),
        "cpu": all_cpu_use,
        "memory": all_memory_use,
    }
    return item


async def query_exchange(events, request=None):
    return {}


async def query_allocation(events, request=None):
    return {}


STATEMENT_MAP = {
    QuotaStatementEnum.analysis: query_analysis,
    QuotaStatementEnum.task: query_task,
    QuotaStatementEnum.allocation: query_allocation,
    QuotaStatementEnum.storage_exchange: query_exchange
}
SERIAL_CODE_MAP = {
    QuotaStatementEnum.analysis: "DA",
    QuotaStatementEnum.task: "DT",
    QuotaStatementEnum.allocation: "DQ",
    QuotaStatementEnum.storage_exchange: "DS",
    "Analysis": "DA",
    "Tasks": "DT",
    "allocation": "DQ",
    "Storage and exchange": "DS"
}


def create_serial_number(statement_type, time_stamp):
    _prefix = SERIAL_CODE_MAP.get(statement_type)
    _counts = UserQuotaStatementModel.objects(statement_type=statement_type).count()
    return f"{_prefix}{time_stamp}{_counts+1}"


async def create_statement(balance: float,
                           original_balance,
                           user: UserModel,
                           operator: UserModel,
                           statement_type: str,
                           remark: Optional[str] = None,
                           event=None,
                           ):
    occurrence_time = datetime.utcnow()
    serial_number = create_serial_number(statement_type, occurrence_time.strftime("%Y%m%d%H%M%S"))
    UserQuotaStatementModel(id=generate_uuid(),
                            serial_number=serial_number,
                            original_balance=original_balance,
                            balance=balance,
                            statement_type=statement_type,
                            occurrence_time=occurrence_time,
                            user=user,
                            operator=operator,
                            use=abs(balance - original_balance),
                            remark=remark,
                            event=event
                            ).save()


async def query_statement(statement_id: Optional[str] = None,
                          user: Optional[str] = None,
                          user_id: Optional[str] = None,
                          email: Optional[str] = None,
                          organization: Optional[str] = None,
                          statement_type: Optional[str] = None,
                          begin_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          order_by: Optional[str] = "-occurrence_time",
                          skip: int = 0,
                          limit: int = 10,
                          request: Optional[Request] = None):
    if order_by is None:
        order_by = "-occurrence_time"
    users_id = None
    if end_time:
        end_time = end_time + " 23:59:59"
    if user_id is None:
        if user or email or organization:
            _user_query = {k: v for k, v in {"name__contains": user,
                                             "organization__contains": organization,
                                             "email__contains": email}.items()
                           if v is not None}
            if _user_query:
                users_id = [i.id for i in UserModel.objects(**_user_query)]
    else:
        users_id = [user_id]
    _query = {k: v for k, v in {"serial_number": statement_id, "user__in": users_id,
                                "statement_type": statement_type, "occurrence_time__gte": begin_time,
                                "occurrence_time__lte": end_time
                                }.items() if v is not None}
    if _query:
        all_statement = UserQuotaStatementModel.objects(**_query).order_by(order_by)
    else:
        all_statement = UserQuotaStatementModel.objects().order_by(order_by)
    total = all_statement.count()
    all_statement = all_statement.skip(skip).limit(limit)
    statement_list = list()
    for _ in all_statement:
        try:
            statement_item = _.to_mongo().to_dict()
            statement_item['occurrence_time'] = _.occurrence_time.strftime('%Y/%m/%d %H:%M:%S')
            statement_item['info'] = await STATEMENT_MAP[_.statement_type](_.event, request)
            statement_item['user'] = _.user.name
            statement_item['operator'] = _.operator.name
            statement_item['remark'] = _.use/StorageQuotaRuleModel.objects.first().storage_quota if _.statement_type == QuotaStatementEnum.storage_exchange else ""
            statement_item.pop('event') if statement_item.get('event') else None
            statement_item['_id'] = _.serial_number
            statement_item['serial_number'] = _.id
            statement_list.append(statement_item)
        except DoesNotExist as e:
            print(e)
    return statement_list, total
