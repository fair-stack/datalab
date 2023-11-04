# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:flow
@time:2022/11/14
"""
import datetime
from mongoengine import (
    StringField,
    IntField,
    DateTimeField,
    ListField,
    DictField,
    ReferenceField,
    Document,
    FloatField,
    GenericReferenceField,
    BooleanField,
)
from app.models.mongo import (
    ToolTaskModel,
    ExperimentModel,
    AnalysisModel2,
    XmlToolSourceModel,
    UserModel,
)
from app.core.config import settings


class FlowModel(Document):
    id = StringField(required=True, primary_key=True)
    # steps_id = ReferenceField(AnalysisStepElementModel, required=True)
    step = IntField()
    steps = IntField(required=True)
    steps_status = ListField(DictField())
    flow_status = StringField()
    create_time = DateTimeField(default=datetime.datetime.utcnow())
    finished_time = DateTimeField()
    steps_time = ListField(DateTimeField())
    user = ReferenceField(UserModel)


class FlowStepModel(Document):
    id = StringField(required=True, primary_key=True)
    flow = ReferenceField(FlowModel, required=True)
    step = IntField(required=True)
    status = StringField(required=True)
    msg = StringField(default="Start execution")
    start_time = DateTimeField(default=datetime.datetime.utcnow())
    end_time = DateTimeField(default=datetime.datetime.utcnow())


class FLowTaskModel(Document):
    id = StringField(required=True, primary_key=True)
    step = ReferenceField(FlowStepModel)
    status = StringField(required=True)
    start_time = DateTimeField(default=datetime.datetime.utcnow())
    end_time = DateTimeField(default=datetime.datetime.utcnow())
    tool = ReferenceField(XmlToolSourceModel)


class TaskQueueModel(Document):
    id = StringField(required=True, primary_key=True)
    event = GenericReferenceField()
    state = StringField(required=True, default=settings.COMPUTING_PENDING, choices=[
        settings.COMPUTING_PENDING,
        settings.COMPUTING_START,
        settings.COMPUTING_SUCCESS,
        settings.COMPUTING_FAILED
    ])
    start_at = DateTimeField(required=True, default=datetime.datetime.utcnow)
    end_at = DateTimeField(default=None)
    user = ReferenceField(UserModel, required=True)
    quota = FloatField(default=None)
    check = BooleanField(required=True, default=False)
    msg = StringField()
