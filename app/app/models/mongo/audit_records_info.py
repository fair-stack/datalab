# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:audit_records_info
@time:2022/10/13
"""
from datetime import datetime

from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    ReferenceField,
    GenericReferenceField,
    IntField,
    BooleanField
)

from .resources import ComputingResourceModel, StorageResourceModel
from .skeleton2 import SkeletonModel2
from .tool_source import XmlToolSourceModel
from .user import UserModel


class AuditRecordsModel(Document):
    id = StringField(primary_key=True)
    applicant = ReferenceField(UserModel)
    auditor = ReferenceField(UserModel, default=None)
    audit_result = StringField(required=True)
    submit_at = DateTimeField(default=datetime.utcnow)
    audit_at = DateTimeField()
    content = StringField()
    component = GenericReferenceField(choices=[XmlToolSourceModel,
                                               ComputingResourceModel,
                                               StorageResourceModel,
                                               SkeletonModel2
                                               ])
    audit_info = StringField()
    audit_type = StringField(required=True, default="Components")
    audit_status = BooleanField(required=True, default=False)
    apply_nums = IntField()


class AuditMessageModel(Document):
    id = StringField(required=True)
    applicant = ReferenceField(UserModel)
    auditor = ReferenceField(UserModel, default=None)
    audit_result = StringField(required=True)
    submit_at = DateTimeField(default=datetime.utcnow)
    audit_at = DateTimeField()
    content = StringField()
    reference_id = StringField()
    audit_info = StringField()
    audit_type = StringField(required=True, default="Components")
    audit_status = StringField(required=True, default=False)


class ComponentsAuditRecords(Document):
    id = StringField(primary_key=True)
    applicant = ReferenceField(UserModel)
    auditor = ReferenceField(UserModel, default=None)
    audit_result = StringField(required=True)
    submit_at = DateTimeField(default=datetime.utcnow)
    audit_at = DateTimeField()
    content = StringField()
    component = ReferenceField(XmlToolSourceModel)
    audit_info = StringField()


