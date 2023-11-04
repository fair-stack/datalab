from datetime import datetime

from mongoengine import (
    BooleanField,
    CASCADE,
    DateTimeField,
    Document,
    ListField,
    ReferenceField,
    StringField,
)

from .user import UserModel


class ExperimentModel(Document):
    """
    """
    id = StringField(primary_key=True)
    is_shared = BooleanField(default=False)
    shared_from_experiment = ReferenceField("self", reverse_delete_rule=CASCADE)
    is_trial = BooleanField(default=False)
    trial_tool_id = StringField()
    name = StringField(required=True)
    description = StringField()
    user = ReferenceField(UserModel, required=True, reverse_delete_rule=CASCADE)
    tasks = ListField(StringField(required=True))
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
