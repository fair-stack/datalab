# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:audit_enumerate
@time:2022/10/31
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditEnumerateSchema(BaseModel):
    audit_type: str
    create_end: datetime
    update_end: Optional[datetime]
    disable_end: Optional[datetime]
    disable: bool
    user: str


class AuditEnumerateRequestSchema(BaseModel):
    audit_type: str
    create_end: datetime
    update_end: Optional[datetime]
    disable_end: Optional[datetime]
    disable: bool = False


