from datetime import datetime

from mongoengine import (
    CASCADE,
    DateTimeField,
    Document,
    ListField,
    ReferenceField,
    StringField,
)

from app.models.mongo.deprecated.skeleton import SkeletonModel

CompoundStepElementInputParam_DEFAULT_DATA_MODES = ("NO_DEFAULT", "DEPENDENCY", "DEFAULT_DATA")


class CompoundStepModel(Document):
    id = StringField(primary_key=True)
    skeleton = ReferenceField(SkeletonModel, reverse_delete_rule=CASCADE)
    name = StringField(required=True)
    description = StringField()
    instruction = StringField()
    multitask_mode = StringField(required=True, default="ALL")   # All tasks are executed： ALL / Select a task to execute（Single selection）： SELECT / Select a task to execute（Single selection）：MULTI_SELECT
    elements = ListField(StringField())
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
