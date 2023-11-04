from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    EmbeddedDocumentField,
    ListField,
    StringField,
)


class PlatformModel(Document):
    """
    """
    id = StringField(primary_key=True)
    name = StringField(required=True, unique=True)
    logo = StringField(required=True)
    copyright = StringField()
    filingNo = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
