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


PERMISSION_CATEGORIES = ("MENU", "OPERATION", "DATA")


class PermissionModel(Document):
    """
    """
    id = StringField(primary_key=True)  # Can be associated with permission_code Be consistent
    code = StringField(required=True)
    name = StringField(required=True)
    is_group = BooleanField(default=False)  # Whether it is a classification and sub-classification， Only the last leaf node is False
    parent = ReferenceField("self", reverse_delete_rule=CASCADE)
    children = ListField(StringField(required=True), default=[])
    category = StringField(choices=PERMISSION_CATEGORIES)
    uri = StringField()
    deleted = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
