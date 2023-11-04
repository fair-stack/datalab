# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:digital_asset
@time:2023/06/07
"""
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
    GenericReferenceField
)

from .user import UserModel
from .experiment import ExperimentModel
from .analysis2 import AnalysisModel2
from .task import ToolTaskModel
from .dataset import DataFileSystem
from enum import Enum
from .public_data import PublicDataFileModel
from .digital import MultilingualGenericsModel

class DataStorageMediumEnum(Enum):
    FILE_SYSTEM: str = "FILE_SYSTEM"
    SQL_DATABASE: str = "SQL"
    NoSQL_DATABASE: str = "NoSQL"


class DigitalAssetTypesModel(Document):
    id = StringField(required=True, primary_key=True)
    storage_medium = EnumField(DataStorageMediumEnum)
    ingestion_plugin = StringField()
    name = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)


class ExperimentsDigitalAssetsModel(Document):
    id = StringField(required=True, primary_key=True)
    name = StringField(required=True)
    is_file = BooleanField(required=True)
    data_size = IntField(required=True)
    data_path = StringField(required=True)
    user = ReferenceField(UserModel)
    description = StringField()
    file_extension = StringField()
    from_source = GenericReferenceField(choices=[DataFileSystem, PublicDataFileModel, MultilingualGenericsModel])
    from_user = ReferenceField(UserModel)
    deleted = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    parent = StringField(default="root")
    project = StringField(default=None)
    task = StringField(default=None)
    typing = ReferenceField(DigitalAssetTypesModel)


class DigitalAssetsModel(Document):
    id = StringField(required=True, primary_key=True)
    parent = StringField(required=True, default="root")
    name = StringField(required=True)
    is_dir = BooleanField(required=True)
    storage_ = StringField(required=True)
    data_size = IntField(required=True)
    data_path = StringField(required=True)
    user = ReferenceField(UserModel)
    description = StringField()
    from_source = StringField(required=True)
    from_user = ReferenceField(UserModel)
    deleted = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    data_type = StringField(required=True, default="myData")
    storage_service = StringField(required=True, default="ext4")
    file_extension = StringField()
    alias_name = StringField()
    child = ListField(StringField())
    deps = IntField(required=True)
    lab_id = StringField()
    task_id = StringField()
    public = StringField()
    public_at = DateTimeField()
