from datetime import datetime
from typing import List, Optional

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    ListField,
    ReferenceField,
    StringField,
)

from .user import UserModel


XmlToolSourceReqFields = [
    "xml_name",
    "folder_name",
    "folder_path",
    "name",
    "version",
    "author",
    "category",
    "executable",
    "command",
    "inputs",
    "outputs"
]


XmlToolSourceInputsReqFields = [
    "name",
    "label",
    "type"
]


XmlToolSourceOutputsReqFields = [
    "name",
    "type"
]


class Requirement(EmbeddedDocument):
    type = StringField(required=True)
    version = StringField(required=True)
    value = StringField(required=True)


class InputParamOption(EmbeddedDocument):
    name = StringField(required=True)
    type = StringField(required=True)
    value = StringField(required=True)


class InputParam(EmbeddedDocument):
    name = StringField(required=True)
    label = StringField(required=True)
    type = StringField(required=True)
    format = StringField()
    required = BooleanField(required=True, default=True)
    default = StringField()
    help = StringField()
    options = ListField(EmbeddedDocumentField(InputParamOption))

    meta = {'allow_inheritance': True}


class OutputData(EmbeddedDocument):
    name = StringField(required=True)
    type = StringField(required=True)
    format = StringField()

    meta = {'allow_inheritance': True}


class TestInputParam(EmbeddedDocument):
    name = StringField(required=False)
    value = StringField(required=False)


class TestOutputData(EmbeddedDocument):
    name = StringField(required=False)
    value = StringField(required=False)


class TestData(EmbeddedDocument):
    inputs = ListField(EmbeddedDocumentField(TestInputParam), required=False)
    outputs = ListField(EmbeddedDocumentField(TestOutputData), required=False)


class XmlToolSourceModel(Document):
    # pk
    id = StringField(primary_key=True)
    # Storage path dependence
    xml_name = StringField(required=True)
    folder_name = StringField(required=True)
    folder_path = StringField(required=True)
    user_space = StringField()
    user = ReferenceField(UserModel)
    # Content fields
    name = StringField(required=True)
    version = StringField(required=True)
    author = StringField(required=True)
    category = StringField(required=True)
    description = StringField()
    requirements = ListField(EmbeddedDocumentField(Requirement))
    executable_path = StringField()
    executable = StringField(required=True)
    entrypoint = StringField()
    command = StringField(required=True)
    # inputs = ListField(EmbeddedDocumentField(InputParam), required=True)
    # outputs = ListField(EmbeddedDocumentField(OutputData), required=True)
    inputs = ListField(DictField())
    outputs = ListField(DictField(), required=True)
    test = EmbeddedDocumentField(TestData)
    help = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    status = BooleanField(default=True)
    language = StringField(required=True)
    audit = StringField(required=True, default='Not committed')   # Not committed，Pending review，Approved by review，Failed to pass the audit
    audit_info = StringField(required=True, default='')
    license = StringField(required=True, default='Apache License 2.0')
    link = StringField(required=True, default='native')
    # https://www.coder.work/article/38570
    # http://docs.mongoengine.org/guide/defining-documents.html
    # Union field uniqueness
    meta = {
        "indexes": [
            {"fields": ("name", "version", "author"), "unique": True}
        ]
    }
