# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:microservices
@time:2023/05/25
"""
from datetime import datetime
from enum import Enum
from mongoengine import (
    Document,
    IntField,
    StringField,
    DateTimeField,
    ReferenceField,
    BooleanField,
    EnumField,
    URLField
)
from .user import UserModel


class MicroservicesServerStateEnum(Enum):
    available = "AVAILABLE"
    unavailable = "UNAVAILABLE"
    pause = "PAUSE"
    upgrade = "UPGRADE"
    maintenance = "MAINTENANCE"


class MicroservicesModel(Document):
    id = StringField(primary_key=True, required=True)
    name = StringField(required=True)
    port = IntField()
    host = URLField(required=True)
    description = StringField(default=None)
    upstream_id = StringField(required=True)
    router_id = StringField(required=True)
    router = StringField(required=True)
    user = ReferenceField(UserModel, required=True)
    integration_at = DateTimeField(default=datetime.utcnow)
    modify_at = DateTimeField(default=datetime.utcnow)
    state = EnumField(MicroservicesServerStateEnum)
    deleted = BooleanField(default=False)
    modify_user = ReferenceField(UserModel, required=True)

