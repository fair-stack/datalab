# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:audit_enumerate
@time:2022/10/31
"""
from datetime import datetime
from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    ReferenceField,
    BooleanField
)
from .user import UserModel


class AuditEnumerateModel(Document):
    id = StringField(primary_key=True)
    user = ReferenceField(UserModel, required=True)
    create_end = DateTimeField(default=datetime.utcnow, required=True)
    update_end = DateTimeField(default=datetime.utcnow, required=True)
    disable_end = DateTimeField()
    audit_type = StringField(required=True)
    disable = BooleanField(default=False, required=True)

