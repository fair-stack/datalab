# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:notebook
@time:2023/02/21
"""
from datetime import datetime
from mongoengine import (
    Document,
    StringField,
    IntField,
    ReferenceField,
    BooleanField,
    DateTimeField,
    ListField,
    GenericReferenceField
)
from app.models.mongo import UserModel, DataFileSystem


class SubjectModel(Document):
    id = StringField(required=True, primary_key=True)
    one_rank_id = StringField(required=True)
    one_rank_name = StringField(required=True)
    one_rank_name_en = StringField(required=True)
    one_rank_no = StringField(required=True)
    two_rank_id = StringField(required=True)
    two_rank_name = StringField(required=True)
    two_rank_name_en = StringField(required=True)
    two_rank_no = StringField(required=True)
    three_rank_id = StringField(required=True)
    three_rank_name = StringField(required=True)
    three_rank_name_en = StringField(required=True)
    three_rank_no = StringField(required=True)


class NoteBookSupportLanguageModel(Document):
    id = StringField(required=True, primary_key=True)
    image = StringField()
    version = StringField(required=True)
    language = StringField(required=True)
    create_at = DateTimeField(default=datetime.utcnow)
    update_at = DateTimeField(default=datetime.utcnow)
    state = BooleanField(default=True)
    icon = StringField()


class NoteBookProjectsModel(Document):
    id = StringField(required=True, primary_key=True)
    name = StringField(required=True)
    create_at = DateTimeField(required=True, default=datetime.utcnow)
    update_at = DateTimeField(required=True, default=datetime.utcnow)
    delete_at = DateTimeField(required=True, default=datetime.utcnow)
    deleted = BooleanField(required=True, default=False)
    description = StringField(default=None)
    user = ReferenceField(UserModel)
    notebook_nums = IntField(default=1)
    upstream_id = StringField(required=True)
    router_id = StringField(required=True)
    router = StringField(required=True, default='/0103cd2')
    cpu = IntField()
    memory = IntField()
    language = ReferenceField(NoteBookSupportLanguageModel)
    subject = StringField()
    data_source = ListField(GenericReferenceField(choices=[DataFileSystem]))


# Temporary use
class UsedPortModel(Document):
    id = StringField(required=True, primary_key=True)
    port = IntField(required=True)
    used = BooleanField(required=True, default=False)
