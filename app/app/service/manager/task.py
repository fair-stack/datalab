# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:task
@time:2023/03/17
"""
import sys
sys.path.append('/Users/wuzhaochen/Desktop/workspace/datalab/app')
import json
from app.models.mongo import (
    UserModel,
    ToolTaskModel,
    AnalysisModel2,
    ExperimentModel,
    TaskQueueModel,
    ComputingQuotaRuleModel,
    UserQuotaModel,
)
from typing import Optional
from app.core.config import settings
from app.utils.common import generate_uuid
from app.service.manager.quota import UserQuotaManager, Cashier


class ComputeResourceException(Exception):
    def __init__(self):
        msg = "Resource exception"


class ComputeTaskManager:

    @staticmethod
    def due(task_id: Optional[str] = None, lab_id: Optional[str] = None,
            compute_type=settings.ComputeEvent.task):
        executor = None
        if compute_type == settings.ComputeEvent.task:
            executor = ToolTaskModel.objects(id=task_id, experiment=lab_id).first()
        elif compute_type == settings.ComputeEvent.analysis:
            executor = AnalysisModel2.objects(id=lab_id).first()
        elif compute_type == settings.ComputeEvent.experiment:
            executor = ExperimentModel.objects(id=lab_id).first()
        if executor is None:
            raise ComputeResourceException()

    @staticmethod
    def add_task(event, user_id):
        task_queue_id = generate_uuid()
        user = UserModel.objects(id=user_id).first()
        task = TaskQueueModel(
            id=task_queue_id,
            user=user,
            event=event,
            task_id=event.id
        )
        try:
            task.save()
        except Exception as e:
            print(e)
            TaskQueueModel(
                id=task_queue_id,
                user=user,
                msg=str(e)
                           ).save()
        return task_queue_id

    @staticmethod
    def failed(task_id):
        TaskQueueModel.objects(id=task_id).update_one(status=settings.COMPUTING_FAILED)

    @staticmethod
    async def success(task_id, publisher):
        _model = TaskQueueModel.objects(id=task_id).first()
        _base_event_id = _model.task_id
        status = await publisher.get(f"{_base_event_id}-task")
        if status == "Error":
            status = settings.COMPUTING_FAILED
        try:
            overhead = await publisher.get(f"{_base_event_id}-resource")
            overhead = json.loads(overhead)
        except Exception as e:
            print(e)
            overhead = dict()
        print(status, type(status), overhead, type(overhead))
        _model.status = status
        _model.overhead = overhead
        try:
            _model.save()
            ComputeTaskManager.deduct(_model)
        except Exception as e:
            _model.status = settings.COMPUTING_FAILED
            _model.msg = str(e)
            _model.save()

    @staticmethod
    def run(task_id):
        TaskQueueModel.objects(id=task_id).update_one(status=settings.COMPUTING_START)

    @staticmethod
    def listen():
        listen_tasks = TaskQueueModel.objects(check=False)
        return [i.id for i in listen_tasks]

    @staticmethod
    def deduct(task_model):
        overhead = task_model.overhead
        _cashier = Cashier()
        quota_list = list()
        _cpu_overhead = overhead['cpu_used_list']
        _memory_overhead = overhead['vms_list']
        if _cpu_overhead:
            for i in _cpu_overhead:
                quota_list.append(_cashier.exchange_rate_computing(i, "CORE", "CPU", 1, "s"))
        else:
            quota_list.append(_cashier.minimum_consumption("CPU"))
        if _memory_overhead:
            for i in _memory_overhead:
                quota_list.append(_cashier.exchange_rate_computing(i, "B", "MEMORY", 1, "s"))
        else:
            quota_list.append(_cashier.minimum_consumption("MEMORY"))
        UserQuotaManager().deduct(task_model, sum(quota_list))


if __name__ == '__main__':
    '25ee84e3f5b344539ddb8d1762'
    from datetime import datetime
    from app.db.mongo_util import connect_mongodb
    from app.models.mongo import AnalysisModel2, ExperimentModel, NoteBookProjectsModel, XmlToolSourceModel, \
        UserModel
    connect_mongodb()
    # task_model = TaskQueueModel.objects(id="25ee84e3f5b344539ddb8d1762").first()
    # overhead = task_model.overhead
    # use_sec = (datetime.strptime(overhead['end_time'], "%Y/%m/%d %H:%M:%S") -
    #            datetime.strptime(overhead['start_time'], "%Y/%m/%d %H:%M:%S")
    #            ).total_seconds()
    # _rule = ComputingQuotaRuleModel.objects.first()
    # use_sec_cpu = reduce(lambda x, y: _rule.cpu_quota * x + y, overhead["cpu_used_list"])
    # use_sec_mem = reduce(lambda x, y: _rule.memory_quota * x + y, overhead["vms_list"])
    # user_quota_model = UserQuotaModel.objects(user=task_model.user).first()
    # print(use_sec_cpu)
    # print(use_sec_mem)
    # balance = float(Decimal(user_quota_model.
    #                         balance - sum([use_sec_cpu, use_sec_mem])
    #                         ))
    # print(balance)
    #
    # _cashier = Cashier()
    # quota_list = list()
    # for i in overhead['cpu_used_list']:
    #     quota_list.append(_cashier.exchange_rate_computing(i, "CORE", "CPU", 1, "s"))
    # for i in overhead['vms_list']:
    #     quota_list.append(_cashier.exchange_rate_computing(i, "B", "MEMORY", 1, "s"))
    # UserQuotaManager().deduct(task_model, sum(quota_list))
