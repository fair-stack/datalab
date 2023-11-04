# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:digital
@time:2023/07/27
"""
from enum import Enum
from datetime import datetime
from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
    ListField,
    EnumField,
)

from .user import UserModel


DATASET_FROM_SOURCE_TYPES = ("UPLOADED", "DERIVED", "ANALYSIS", "PROGRAM")


class FileDigitalSource(Enum):
    upload = "UPLOADED"
    derived = "DERIVED"
    analysis = "ANALYSIS"
    lab = "LAB"
    program = "PROGRAM"


class FileDigital(Document):
    id = StringField(required=True, primary_key=True)  # Unique identification
    name = StringField(required=True)  # Entity file name
    is_dir = BooleanField(required=True)  # Folder or not， Folders are not essentially entities
    repositories = StringField(required=True)  # Repository/bucket logo
    data_size = IntField(required=True)  # Storage entity size
    object_identifier = StringField(required=True)  # logo/Path/id
    doi = StringField()  # To be extendeddoiUse the， Temporary splicing only docking internal data
    user = ReferenceField(UserModel)  # Person of attribution
    description = StringField()  # File Description
    from_source = EnumField(FileDigitalSource, required=True)  # Source<Upload, experiment, tools, online programming>
    deleted = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    storage_service = StringField(required=True, default="lake")
    file_extension = StringField()  # File extension
    parent = StringField(default="root")  # Parent levelid


class MultilingualGenericsModel(Document):
    id = StringField(required=True, primary_key=True)
    language = StringField(required=True)
    type = StringField(required=True)
    frontend = StringField(required=True)
    data = StringField(required=True)
    serialize = StringField()
