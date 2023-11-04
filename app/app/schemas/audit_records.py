# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:audit_records
@time:2022/10/13
"""
import datetime
from pydantic import BaseModel


class ComponentsAuditRecordsSchema(BaseModel):
    id: str
    applicant: str
    auditor: str = None
    audit_result: str
    submit_at: str
    audit_at: str = None
    content: str
    component: str
    audit_info: str = None


class AuditRecordsSchema(BaseModel):
    id: str
    applicant: str
    auditor: str = None
    audit_result: str
    submit_at: str
    audit_at: str = None
    content: str = None
    # component: dict = None
    audit_info: str = None
    audit_type: str
    apply_nums: int = None
