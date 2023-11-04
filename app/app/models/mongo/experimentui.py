from datetime import datetime

from mongoengine import (
    DateTimeField,
    Document,
    StringField,
)


class ExperimentUiModel(Document):
    """
    """
    id = StringField(primary_key=True)
    intro = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
