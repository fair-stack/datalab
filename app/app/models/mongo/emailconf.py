from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    EmbeddedDocumentField,
    IntField,
    ListField,
    StringField,
)


class EmailConfModel(Document):
    """
    SSL Protocol port：465
    non SSL Protocol port：25

    The default is： SSL + port 465
    """
    id = StringField(primary_key=True)
    is_default = BooleanField(required=True)    # logo，Built-in or not cas The mail service；If it is a custom email，the False
    is_selected = BooleanField(required=True)   # Check it or not
    name = StringField(required=True)       # E-mail service of Science Data Center, Chinese Academy of Sciences / Custom mail service
    use_tls = BooleanField()
    port = IntField()
    host = StringField()
    user = StringField()
    password_encrypted = StringField()   # You need to decrypt it when you use it
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
