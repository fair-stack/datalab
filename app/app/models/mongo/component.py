# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:component
@time:2022/09/01
"""
from mongoengine import (
    Document,
    StringField,
    IntField,
    BooleanField,
    ReferenceField
)
from app.models.mongo import XmlToolSourceModel


class ComponentInstance(Document):
    id = StringField(primary_key=True)
    component_name = StringField(required=True)
    synchronous_uri = StringField(required=True)
    asynchronous_uri = StringField(required=True)
    image_name = StringField(required=True)
    docker_file = StringField(required=True)
    uri_type = StringField(required=True)
    serialization = BooleanField(default=False)
    component_type = StringField(required=True)
    base_id = ReferenceField(XmlToolSourceModel, required=True)
    occupy = IntField()
