# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:resources
@time:2022/11/09
"""


from datetime import datetime
from enum import Enum
from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
    FloatField,
    EnumField,
    GenericReferenceField,
)

from .user import UserModel
from .task import ToolTaskModel
from .analysis2 import AnalysisModel2


class StorageResourceModel(Document):
    id = StringField(primary_key=True)
    apply = BooleanField(required=True, default=True)
    allocated_user = ReferenceField(UserModel)
    allocated_time = DateTimeField(default=datetime.utcnow)
    last_update_time = DateTimeField(default=datetime.utcnow)
    last_update_user = ReferenceField(UserModel)
    newcomer = IntField(required=True, default=5368709120)


class QuotaResourceModel(Document):
    id = StringField(primary_key=True)
    apply = BooleanField(required=True, default=True)
    allocated_user = ReferenceField(UserModel)
    allocated_time = DateTimeField(default=datetime.utcnow)
    last_update_time = DateTimeField(default=datetime.utcnow)
    last_update_user = ReferenceField(UserModel)
    newcomer = IntField(required=True, default=100)


class StorageResourceAllocatedModel(Document):
    id = StringField(primary_key=True)
    user = ReferenceField(UserModel)
    allocated_storage_size = IntField(required=True)
    allocated_user = ReferenceField(UserModel)
    allocated_time = DateTimeField(default=datetime.utcnow)
    last_update_time = DateTimeField(default=datetime.utcnow)
    apply = BooleanField(required=True, default=True)


class ComputingResourceModel(Document):
    id = StringField(primary_key=True)
    name = StringField(required=True)
    allocated_user = ReferenceField(UserModel)
    computing_core = StringField(required=True)
    core_nums = IntField(required=True, default=1)
    memory_nums = IntField(required=True, default=1024)
    description = StringField(required=True, default="The platform can allocate computing resources")
    apply = BooleanField(required=True, default=True)
    user_count = IntField(required=True, default=0)
    allocated_time = DateTimeField(default=datetime.utcnow)
    last_update_time = DateTimeField(default=datetime.utcnow)
    last_update_user = ReferenceField(UserModel)


class ComputingResourceAllocatedModel(Document):
    id = StringField(primary_key=True)
    user = ReferenceField(UserModel)
    computing_resource_base = ReferenceField(ComputingResourceModel)
    allocated_user = ReferenceField(UserModel)
    allocated_use_time = IntField(required=True, default=0)
    allocated_time = DateTimeField(default=datetime.utcnow)
    last_update_time = DateTimeField(default=datetime.utcnow)


class ComputingQuotaRuleModel(Document):
    id = StringField(primary_key=True)
    cpu_quota = FloatField(required=True, default=0.002)
    cpu_unit_measurement = StringField(required=True, default='CORE/s')
    memory_quota = FloatField(required=True, default=0.0001)
    memory_unit_measurement = StringField(required=True, default='GB/s')
    gpu_quota = FloatField(required=True, default=0.01)
    gpu_unit_measurement = StringField(required=True, default="GPU/s")
    create_at = DateTimeField(required=True, default=datetime.utcnow)
    update_at = DateTimeField(required=True, default=datetime.utcnow)
    user = ReferenceField(UserModel, required=True)


class StorageQuotaRuleModel(Document):
    id = StringField(primary_key=True)
    storage_quota = FloatField(required=True, default=5)
    storage_unit_measurement = StringField(required=True, default='GB')
    create_at = DateTimeField(required=True, default=datetime.utcnow)
    update_at = DateTimeField(required=True, default=datetime.utcnow)
    user = ReferenceField(UserModel, required=True)
    enable = BooleanField(required=True, default=True)


class UserQuotaModel(Document):
    id = StringField(primary_key=True)
    user = ReferenceField(UserModel, required=True)
    quota = FloatField(required=True)
    balance = FloatField(required=True)
    create_at = DateTimeField(required=True, default=datetime.utcnow)
    update_at = DateTimeField(required=True, default=datetime.utcnow)


class QuotaStatementEnum(Enum):
    task = "Tasks"
    analysis = "Analysis"
    allocation = "allocation"
    storage_exchange = "Storage and exchange"


class UserQuotaStatementModel(Document):
    id = StringField(primary_key=True)
    original_balance = FloatField(required=True)
    balance = FloatField(required=True)
    statement_type = EnumField(QuotaStatementEnum)
    occurrence_time = DateTimeField(required=True, default=datetime.utcnow)
    use = FloatField(required=True)
    user = ReferenceField(UserModel, required=True)
    operator = ReferenceField(UserModel, required=True)
    event = GenericReferenceField(choices=[
        ToolTaskModel,
        StorageResourceAllocatedModel,
        AnalysisModel2
                                               ]
                                  )
    remark = StringField()
    serial_number = StringField()


class PlatformResourceModel(Document):
    storage = FloatField(required=True, default=1099511627776)
    memory = FloatField(required=True, default=440*1024**2)
    cpu = IntField(required=True, default=36)
    id = StringField(required=True, primary_key=True)
