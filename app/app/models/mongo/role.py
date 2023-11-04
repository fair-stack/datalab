from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    ListField,
    StringField,
)


class RoleModel(Document):
    """
    """
    id = StringField(primary_key=True)
    name = StringField(required=True, unique=True)
    permissions = ListField(DictField())
    is_innate = BooleanField(required=True, default=False)
    is_default_role = BooleanField(default=False)
    creator = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
