from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    CASCADE,
    DENY,
    Document,
    NULLIFY,
    ReferenceField,
    StringField,
)

from .role import RoleModel


class UserModel(Document):
    """
    """
    id = StringField(primary_key=True)
    name = StringField(required=True)
    email = StringField(unique=True, required=True)
    organization = StringField()
    hashed_password = StringField()
    password_strength = StringField()
    role = ReferenceField(RoleModel, reverse_delete_rule=NULLIFY)
    avatar = StringField()
    is_email_verified = BooleanField(default=False)
    is_active = BooleanField(default=True)
    is_superuser = BooleanField(default=False)
    from_source = StringField(default="signup")   # signup, umt
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
