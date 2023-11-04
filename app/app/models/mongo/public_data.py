from mongoengine import Document, StringField, IntField, ReferenceField, DateTimeField, BooleanField,EmbeddedDocumentField, ListField
from app.models.mongo import UserModel
from datetime import datetime

from mongoengine import Document, StringField, ListField, EmbeddedDocument, EmbeddedDocumentField


class DatasetsAuthorModel(EmbeddedDocument):
    name = StringField(required=True)
    email =StringField()
    org = StringField()

class PublicDatasetOptionModel(Document):
    id = StringField(required=True, primary_key=True)
    access = BooleanField(required=True, default=True)
    user = ReferenceField(UserModel, required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)


class PublicDatasetModel(Document):
    id = StringField(required=True, primary_key=True)
    icon = StringField(required=True)
    name = StringField(required=True)
    access = StringField(required=True, default="PUBLIC")
    label = StringField(required=True)
    data_type = StringField(required=True)
    user = ReferenceField(UserModel, required=True)
    links = StringField(required=True, default="LOCAL")
    files = IntField(default=0)
    data_size = IntField(default=0)
    organization_name = StringField()
    date_published =  StringField()
    description = StringField()
    ftp_user = StringField()
    ftp_password = StringField()
    ftp_ip = StringField()
    ftp_port = StringField()
    name_zh = StringField()
    name_en = StringField()
    author = ListField(EmbeddedDocumentField(DatasetsAuthorModel), default=list)





class PublicDataFileModel(Document):
    id = StringField(required=True, primary_key=True)
    datasets = ReferenceField(PublicDatasetModel, required=True)
    name = StringField(required=True)
    data_path = StringField(required=True)
    data_size = IntField(required=True)
    access = StringField(required=True, default="PUBLIC")
    deleted = BooleanField(required=True, default=False)
    user = ReferenceField(UserModel)
    is_file = BooleanField(required=True)
    store_name = StringField(required=True)
    description = StringField()
    from_source = StringField(required=True)
    from_user = ReferenceField(UserModel)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    data_type = StringField(required=True, default="myData")
    storage_service = StringField(required=True, default="ext4")
    file_extension = StringField()
    uploading = BooleanField(default=False)
    parent = StringField(default="root")
    deps = IntField(required=True)
