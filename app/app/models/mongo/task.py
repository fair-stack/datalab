from datetime import datetime

from mongoengine import (
    CASCADE,
    DateTimeField,
    DictField,
    Document,
    DO_NOTHING,
    ListField,
    ReferenceField,
    StringField,
)

from .experiment import ExperimentModel
from .tool_source import XmlToolSourceModel
from .user import UserModel


class ToolTaskModel(Document):
    """
    When adding components to an experiment，Generate corresponding to this task Examples
    """
    id = StringField(primary_key=True)
    name = StringField()
    description = StringField()
    tool = ReferenceField(XmlToolSourceModel)
    experiment = ReferenceField(ExperimentModel, reverse_delete_rule=CASCADE)
    user = ReferenceField(UserModel)
    inputs = ListField(DictField())
    outputs = ListField(DictField())
    status = StringField()  # Success, Error, Pending
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
