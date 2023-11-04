# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:quota
@time:2023/03/17
"""

import sys
from fastapi import status
from fastapi.responses import JSONResponse
from aioredis import Redis
from datetime import datetime
from typing import Optional, Union
from decimal import Decimal, ROUND_UP, ROUND_CEILING
sys.path.append('/Users/wuzhaochen/Desktop/workspace/datalab/app')
from app.models.mongo import (
    UserQuotaModel,
    UserQuotaStatementModel,
    UserModel,
    QuotaStatementEnum,
    QuotaResourceModel,
    PlatformResourceModel,
    StorageResourceAllocatedModel,
    ToolTaskModel,
    ExperimentModel,
    AnalysisModel2,
    TaskQueueModel,
    ComputingQuotaRuleModel,
    StorageQuotaRuleModel
)
from app.utils.statement import create_serial_number
from app.utils.common import generate_uuid
from app.errors.resource import ResourceRuleUnitException, ResourceTransgressionException, \
    ResourceUnDistributableException


AVAILABLE_GPU_RESOURCES_UNITS_TYPES = {"GPU"}
AVAILABLE_CPU_RESOURCES_UNITS_TYPES = {"CORE"}
AVAILABLE_MEMORY_RESOURCES_UNITS_TYPES = {"GB", "MB", "KB", "B"}
AVAILABLE_STORAGE_RESOURCES_UNITS_TYPES = {"TB", "GB", "MB", "KB", "B", "b"}
AVAILABLE_TIME_UNITS_TYPES = {"s", "m", "h", "S", "M", "H"}


def accuracy_correction(num: float):
    return float(Decimal(num).quantize(Decimal('.0000'), rounding=ROUND_UP))


def resource_id(model) -> str:
    return f"{model.id}-resource"


def resource_unit_split(units: str):
    _units = units.split('/')
    if len(_units) == 2:
        _unit, _time = _units
        if _unit not in AVAILABLE_MEMORY_RESOURCES_UNITS_TYPES and _unit not in AVAILABLE_CPU_RESOURCES_UNITS_TYPES \
                and _unit not in AVAILABLE_GPU_RESOURCES_UNITS_TYPES:
            raise ResourceRuleUnitException(f"Abnormal resource conversion unit， Current unit：{_unit}")
        elif _time not in AVAILABLE_TIME_UNITS_TYPES:
            raise ResourceRuleUnitException(f"Resource time unit of measurement is abnormal，Current unit：{_time}，"
                                            f"Platform identifiable units：{AVAILABLE_TIME_UNITS_TYPES}")
        else:
            return _unit, _time
    raise ResourceRuleUnitException(f"Abnormal resource conversion unit: {units}")


class Quantity:

    def __init__(self, quantity: Union[float, int]):
        self._quantity = accuracy_correction(quantity)

    @property
    def quantity(self) -> float:
        return self._quantity


class Cashier:

    def __init__(self):
        self.computing_cash_rule = ComputingQuotaRuleModel.objects.order_by("-update_at").first()
        self.storage_cash_rule = StorageQuotaRuleModel.objects.order_by("-update_at").first()
        self.unit_rate_map = {
            "STORAGE": {"TB": 1024**4, "GB": 1024**3, "MB": 1024**2, "KB": 1024, "B": 1, "b": 0.1},
            "CPU": {"CORE": 1},
            "MEMORY": {"GB": 1024**3, "MB": 1024**2, "KB": 1024, "B": 1},
            "GPU": {"GPU": 1},
            "TIME": {"H": 60**2, "h": 60**2, "M": 60, "m": 60, "S": 1, "s": 1},
        }

    @property
    def storage_bytes_rate(self) -> float:
        # The rules currently set by the platform are forced to unify the proportion as a quota/Storage per byte
        _to_bytes_quota = self.storage_cash_rule.storage_quota/self. \
            unit_rate_map['STORAGE'][self.storage_cash_rule.storage_unit_measurement]
        return _to_bytes_quota

    @property
    def computing_cpu_rate(self) -> float:
        # The rules currently set by the platform are forced to unify as the core/seconds
        _unit, _time = resource_unit_split(self.computing_cash_rule.cpu_unit_measurement)
        return self.computing_cash_rule.cpu_quota / (self.unit_rate_map["CPU"][_unit] /
                                                     self.unit_rate_map["TIME"][_time])

    @property
    def computing_memory_rate(self) -> float:
        # The rules currently set by the platform are forced to be unified into bytes/seconds
        _unit, _time = resource_unit_split(self.computing_cash_rule.memory_unit_measurement)
        return self.computing_cash_rule.memory_quota / (self.unit_rate_map["MEMORY"][_unit] /
                                                        self.unit_rate_map["TIME"][_time])

    @property
    def computing_gpu_rate(self) -> float:
        # The rules currently set by the platform are forced to unify as the core/seconds
        _unit, _time = resource_unit_split(self.computing_cash_rule.gpu_unit_measurement)
        return self.computing_cash_rule.gpu_quota / (self.unit_rate_map["GPU"][_unit] /
                                                     self.unit_rate_map["TIME"][_time])

    def exchange_rate_storage(self, quantity: Union[float, int], units: str) -> float:
        if units not in AVAILABLE_STORAGE_RESOURCES_UNITS_TYPES:
            raise ResourceRuleUnitException(f"Conversion unit is abnormal: {units}")
        _to_bytes = quantity * self.unit_rate_map['STORAGE'][units]
        _use_quota = _to_bytes * self.storage_bytes_rate
        return accuracy_correction(_use_quota)

    def exchange_rate_computing(self, quantity: Union[float, int], units: str,
                                resource_type: str, use_time: float, time_unit: str) -> float:
        if resource_type == "CPU" and units not in AVAILABLE_CPU_RESOURCES_UNITS_TYPES:
            raise ResourceRuleUnitException(f"CPUAbnormal resource conversion unit: {units}")
        elif resource_type == "GPU" and units not in AVAILABLE_GPU_RESOURCES_UNITS_TYPES:
            raise ResourceRuleUnitException(f"GPUAbnormal resource conversion unit: {units}")
        elif resource_type == "MEMORY" and units not in AVAILABLE_MEMORY_RESOURCES_UNITS_TYPES:
            raise ResourceRuleUnitException(f"Abnormal resource conversion unit: {units}")
        elif time_unit not in AVAILABLE_TIME_UNITS_TYPES:
            raise ResourceRuleUnitException(f"Resource conversion time unit is abnormal: {units}")
        _time_rate = use_time * self.unit_rate_map['TIME'][time_unit]
        computing_resource_rate = self.unit_rate_map[resource_type][units]
        _need_quantity = quantity * (computing_resource_rate * _time_rate)
        _use_quota = 0.0
        if resource_type == "CPU":
            _use_quota = _need_quantity * self.computing_cpu_rate
            if int(_use_quota) == 0:
                _use_quota = self.computing_cpu_rate
        elif resource_type == "GPU":
            _use_quota = _need_quantity * self.computing_gpu_rate
        elif resource_type == "MEMORY":
            _use_quota = _need_quantity * self.computing_memory_rate
            if int(_use_quota) == 0:
                _use_quota = self.computing_memory_rate
        return accuracy_correction(_use_quota)

    def minimum_consumption(self, resource_type: str):
        if resource_type == "CPU":
            _use_quota = self.computing_cpu_rate
        elif resource_type == "GPU":
            _use_quota = self.computing_gpu_rate
        elif resource_type == "MEMORY":
            _use_quota = self.computing_memory_rate
        else:
            return 0
        return accuracy_correction(_use_quota)


class UserQuotaManager:
    model = None

    def _model(self, user: UserModel):
        self.model = UserQuotaModel.objects(user=user).first()

    def _task(self, task: ToolTaskModel, use: float) -> UserQuotaStatementModel:
        _statement_id = generate_uuid()
        original = self.user_balance(task.user)
        occurrence_time = datetime.utcnow()
        serial_number = create_serial_number(QuotaStatementEnum.task, occurrence_time.strftime("%Y%m%d%H%M%S"))
        _statement_model = UserQuotaStatementModel(id=_statement_id,
                                                   event=task,
                                                   operator=task.user,
                                                   user=task.user,
                                                   original_balance=original,
                                                   balance=accuracy_correction(original - use),
                                                   use=use,
                                                   statement_type=QuotaStatementEnum.task,
                                                   serial_number=serial_number,
                                                   occurrence_time=occurrence_time
                                                   )
        return _statement_model

    def _analysis(self, analysis: AnalysisModel2, use: float) -> UserQuotaStatementModel:
        _statement_id = generate_uuid()
        original = self.user_balance(analysis.user)
        occurrence_time = datetime.utcnow()
        serial_number = create_serial_number(QuotaStatementEnum.analysis, occurrence_time.strftime("%Y%m%d%H%M%S"))
        _statement_model = UserQuotaStatementModel(id=_statement_id,
                                                   event=analysis,
                                                   operator=analysis.user,
                                                   user=analysis.user,
                                                   original_balance=original,
                                                   balance=accuracy_correction(original - use),
                                                   use=use,
                                                   statement_type=QuotaStatementEnum.analysis,
                                                   occurrence_time=occurrence_time,
                                                   serial_number=serial_number
                                                   )
        return _statement_model

    def _create(self, user, balance: Optional[float] = None):
        if balance is None:
            balance = accuracy_correction(QuotaResourceModel.objects.first().newcomer)
        else:
            balance = accuracy_correction(balance)
        self.model = UserQuotaModel(id=generate_uuid(),
                                    user=user,
                                    quota=balance,
                                    balance=balance
                               )
        try:
            self.model.save()
        except Exception as e:
            return None
        return self.model

    @staticmethod
    def delete(quota_id: str):
        try:
            UserQuotaModel.objects(id=quota_id).delete()
        except Exception as e:
            return None
        return True

    @staticmethod
    def apply_platform_resources(
            storage_size: Optional[int] = None,
            memory_size: Optional[int] = None,
            cpu: Optional[int] = None
                       ):
        _platform_allocation_resource = PlatformResourceModel.objects.first()
        if storage_size is not None:
            all_allocated_storage_size = StorageResourceAllocatedModel.\
                objects().sum("allocated_storage_size")
            if _platform_allocation_resource.storage-all_allocated_storage_size > storage_size:
                return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                    content={"msg": "The free storage resources of the platform are not enough to allocate the storage you need！"})
            else:
                return True
        # if memory_size is not None:
        #     if memory_size < _platform_allocation_resource.storage:
        #         pass
        #     else:
        #         return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        #                             content={"msg": "The platform currently available memory resources are not enough to support you to launch the task，Please try again later."})
        if cpu is not None:
            if cpu < _platform_allocation_resource.cpu:
                pass
            else:
                return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                    content={"msg": "Platform currently availableCPUYou do not have enough resources to launch the task，Please try again later."})
        # Adequate resources
        return True

    @staticmethod
    def user_balance(user: UserModel):
        try:
            return UserQuotaModel.objects(user=user).first().balance
        except Exception as e:
            print(e)
            return 0

    @staticmethod
    def user_balance_is_sufficient(
            user: UserModel,

    ) -> bool:
        _sufficient = None
        _user_quota_model = UserQuotaManager.user_balance(user)
        return _sufficient

    def deduct(self, event, quantity):
        self._model(event.user)
        if isinstance(event, TaskQueueModel):
            if isinstance(event.event, ToolTaskModel):
                statement = self._task(event.event, quantity)
            elif isinstance(event.event, AnalysisModel2):
                statement = self._analysis(event.event, quantity)
            else:
                return False
            self.model.balance = statement.balance
            statement.save()
            self.model.save()
            return True


if __name__ == '__main__':
    import requests
    from app.db.mongo_util import connect_mongodb
    from app.models.mongo import AnalysisModel2, ExperimentModel, NoteBookProjectsModel, XmlToolSourceModel, \
        UserModel
    from datetime import datetime
    connect_mongodb()
    task_model = TaskQueueModel.objects(id="25ee84e3f5b344539ddb8d1762").first()
    overhead = task_model.overhead
    use_sec = (datetime.strptime(overhead['end_time'], "%Y/%m/%d %H:%M:%S") -
               datetime.strptime(overhead['start_time'], "%Y/%m/%d %H:%M:%S")
               ).total_seconds()
    # _rule = ComputingQuotaRuleModel.objects.first()
    _cashier = Cashier()
    quota_list = list()
    for i in overhead['cpu_used_list']:
        quota_list.append(_cashier.exchange_rate_computing(i, "CORE", "CPU", 1, "s"))
    for i in overhead['vms_list']:
        quota_list.append(_cashier.exchange_rate_computing(i, "B", "MEMORY", 1, "s"))
    UserQuotaManager().deduct(task_model, sum(quota_list))

    # use_sec_cpu = reduce(lambda x, y: _rule.cpu_quota * x + y, overhead["cpu_used_list"])
    # use_sec_mem = reduce(lambda x, y: _rule.memory_quota * x + y, overhead["vms_list"])
    # user_quota_model = UserQuotaModel.objects(user=task_model.user).first()
    # print(use_sec_cpu)
    # print(use_sec_mem)
    # balance = float(Decimal(user_quota_model.
    #                         balance - sum([use_sec_cpu, use_sec_mem])
    #                         ))
    # print(balance)
    # Test case  exchange resource to statement with datalab platform, class QuotaManager create statement to model
    # QuotaManager base depends event < storage exchange, compute[Unit], analysis[FLOW]>
    # print(Cashier().exchange_rate_storage(1, "TB"))
    # print(Cashier().exchange_rate_computing(1, "CORE", "CPU", 10, "s"))
    # print(Cashier().exchange_rate_computing(2, "GB", "MEMORY", 10, 's'))
    # print(Cashier().exchange_rate_computing(3, "GPU", "GPU", 3, "s"))
    #
    # def test():
    #     current_user = UserModel.objects(id='0993bc4a65fa4d638dcdcf44030f7194').first()
    #     _quota_rule = StorageQuotaRuleModel.objects.first()
    #     unit_map = {
    #         "KB": 1024,
    #         "MB": 1024 ** 2,
    #         "GB": 1024 ** 3,
    #         "TB": 1024 ** 4
    #     }
    #     try:
    #         if _quota_rule is not None:
    #             _exchange_value = _quota_rule.storage_quota
    #             user_quota = UserQuotaModel.objects(user=current_user).first()
    #             _need_quota = _exchange_value * storage_size
    #             original_balance = user_quota.balance
    #             if _need_quota <= user_quota.balance:
    #                 user_quota.update(balance=original_balance - _need_quota)
    #                 _balance = original_balance - _need_quota
    #                 _storage_resource = StorageResourceAllocatedModel.objects(user=current_user).first()
    #                 _storage_resource.update(
    #                     allocated_storage_size=_storage_resource.allocated_storage_size + storage_size * unit_map[
    #                         _quota_rule.storage_unit_measurement])
    #                 return JSONResponse(status_code=status.HTTP_200_OK,
    #                                     content={"msg": "Successful!"}
    #                                     )
    #             else:
    #                 nee_some_storage = f"{storage_size}/{_quota_rule.storage_unit_measurement}"
    #                 return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
    #                                     content={"msg": f"The current balance is not sufficient for conversion{nee_some_storage}Amount of storage resources,To exchange this amount of resources{_need_quota}quota！"})
    #     except Exception as e:
    #         return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
    #                             content={"msg": f"Exchange failure，{e}!"})



