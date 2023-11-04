# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:resources
@time:2022/11/09
"""
from pydantic import BaseModel
from typing import Optional


class StorageResourceSchema:
    id: str = None
    apply: bool
    allocated_user: str
    last_update_time: str
    allocated_user: str
    last_update_user: str


class StorageResourceAllocateSchema(BaseModel):
    id: str
    user: str
    allocated_storage_size: int
    used_size: int = 0
    allocated_user: str
    allocated_time: str
    last_update_time: str


class StorageResourceAllocateCreateSchema(BaseModel):
    user: str
    allocated_storage_size: int


class ComputingResourceSchema(BaseModel):
    id: str
    name: str
    computing_core: str
    description: str
    core_nums: int
    memory_nums: int
    apply: bool
    user_count: int
    allocated_user: str
    allocated_time: str
    last_update_time: str
    last_update_user: str


class ComputingResourceAllocatedSchema(BaseModel):
    id: str
    user: str
    computing_resource_base: str
    allocated_user: str
    allocated_use_time: int
    allocated_time: str
    last_update_time: str


class ComputingResourceAllocatedResponseSchema(BaseModel):
    id: str
    name: str
    computing_resource_base: str
    allocated_user: str
    allocated_use_time: int
    allocated_time: str
    computing_core: str
    description: str
    core_nums: int
    memory_nums: int


class ComputingQuotaRuleSchema(BaseModel):
    id = str
    cpu_quota: float
    cpu_unit_measurement: str
    memory_quota: float
    memory_unit_measurement: str
    gpu_quota: float
    gpu_unit_measurement: str
    create_at: str
    update_at: str
    user: str


class StorageQuotaRuleSchema(BaseModel):
    id: str
    storage_quota: float
    storage_unit_measurement: str
    create_at: str
    update_at: str
    user: str
    enable: bool


class UserQuotaSchema(BaseModel):
    id: str
    user: str
    quota: float
    create_at: str
    update_at: str


class UserQuotaStatementSchema(BaseModel):
    id: str
    original_balance: float
    balance: float
    statement_type: str
    occurrence_time: str
    use: float
    user: str
    remark: Optional[str] = None
