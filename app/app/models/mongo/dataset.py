from datetime import datetime
from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
    ListField,
)

from .user import UserModel


DATASET_FROM_SOURCE_TYPES = ("UPLOADED", "DERIVED", "ANALYSIS")


class DatasetModel(Document):
    """
    from_source:
        - UPLOADED: Uploaded data（file，file root dir）
        - DERIVED：filefile
        - <task_id>: `data_type` = `taskData` when，Identifies the one that produced this data record task_id

    data_type:
        - myData: My Data
        - taskData: Experimental data
    """
    id = StringField(primary_key=True)
    name = StringField(required=True)
    is_file = BooleanField(required=True, default=True)
    file_extension = StringField()
    store_name = StringField(required=True)
    data_size = IntField()
    data_path = StringField(required=True)
    user = ReferenceField(UserModel)
    description = StringField()
    from_source = StringField(required=True, choices=DATASET_FROM_SOURCE_TYPES)
    from_user = ReferenceField(UserModel)
    deleted = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    data_type = StringField(required=True, default="myData")
    storage_service = StringField(required=True, default="ext4")


class DataFileSystem(Document):
    id = StringField(required=True, primary_key=True)
    name = StringField(required=True)
    is_file = BooleanField(required=True)
    is_dir = BooleanField(required=True)
    store_name = StringField(required=True)
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
    parent = StringField(default="root")
    child = ListField(StringField())
    deps = IntField(required=True)
    lab_id = StringField()
    task_id = StringField()
    public = StringField()
    public_at = DateTimeField()
