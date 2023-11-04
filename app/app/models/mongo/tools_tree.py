# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:tools_tree
@time:2022/10/12
"""
import uuid
from datetime import datetime
from mongoengine import (
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
)
from .user import UserModel


class ToolsTreeModel(Document):
    """
    """
    id = StringField(primary_key=True)
    name = StringField(required=True)
    level = IntField(default=1)
    parent = StringField(required=True, default='root')
    user = ReferenceField(UserModel, required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)


if __name__ == '__main__':
    ...
