# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:standalone_container
@time:2023/07/04
"""
from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    ListField,
    ReferenceField,
    IntField,
    StringField,
)
from datetime import datetime
from .tool_source import XmlToolSourceModel
from .user import UserModel


class StandaloneContainerModel(Document):
    id = StringField(primary_key=True)
    name = StringField(required=True)
    image = StringField(required=True)
    create_at = DateTimeField(default=datetime.utcnow)
    deleted = BooleanField(required=False)
    deleted_at = DateTimeField()
    port = IntField()
    commands = ListField()
    parameters = DictField()
    tool = ReferenceField(XmlToolSourceModel)
    author = ReferenceField(UserModel)


if __name__ == '__main__':
    ...
