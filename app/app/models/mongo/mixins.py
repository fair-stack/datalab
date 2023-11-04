from datetime import datetime

from mongoengine import (
    BooleanField,
    CASCADE,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    EmbeddedDocumentListField,
    EmailField,
    ListField,
    ReferenceField,
    StringField,
)


class DateTimeModelMixin(Document):
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
