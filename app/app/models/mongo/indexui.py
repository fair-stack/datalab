from datetime import datetime

from mongoengine import (
    DateTimeField,
    DictField,
    Document,
    StringField,
)


class IndexUiModel(Document):
    """
    """
    id = StringField(primary_key=True)
    title = StringField()
    intro = StringField()
    background = StringField()
    styles_start = DictField()
    styles_stats = DictField()
    styles_copyright = DictField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
