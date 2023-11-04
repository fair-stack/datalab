# -*- coding = UTF-8 -*-
from datetime import datetime
from mongoengine import (
    Document,
    IntField,
    DictField,
    ListField,
    FloatField,
    StringField,
    DateTimeField,
    ReferenceField,
    GenericReferenceField,
)
from app.core.config import settings
from .user import UserModel
from .task import ToolTaskModel
from .experiment import ExperimentModel
from .analysis2 import AnalysisModel2
from .tool_source import XmlToolSourceModel

    
class TaskResourceModel(Document):
    id = StringField(required=True, primary_key=True)
    min_rss = FloatField()
    max_rss = FloatField()
    min_vms = FloatField()
    max_vms = FloatField()
    min_memory_percent = FloatField()
    max_memory_percent = FloatField()
    min_cpu_used = FloatField()
    max_cpu_used = FloatField()
    rss_list = ListField()
    vms_list = ListField()
    memory_percent_list = ListField()
    cpu_used_list = ListField()
    start_time = DateTimeField()
    end_time = DateTimeField()


class TaskQueueModel(Document):
    id = StringField(required=True, primary_key=True)
    start_at = DateTimeField(default=datetime.utcnow)
    end_at = DateTimeField(default=datetime.utcnow())
    event = GenericReferenceField(choices=[ToolTaskModel, ExperimentModel, AnalysisModel2])
    task_id = StringField(required=True)
    user = ReferenceField(UserModel)
    resources = ReferenceField(TaskResourceModel)
    component = ReferenceField(XmlToolSourceModel)
    status = StringField(required=True,
                         default=settings.COMPUTING_PENDING,
                         choices=[
                             settings.COMPUTING_PENDING,
                             settings.COMPUTING_START,
                             settings.COMPUTING_SUCCESS,
                             settings.COMPUTING_FAILED]
                         )
    stage = IntField(default=0)
    quota = FloatField(default=None)
    msg = StringField()
    overhead = DictField()
    depends = StringField()
    steps = IntField(default=0)







