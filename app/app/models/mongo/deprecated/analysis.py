from datetime import datetime

from mongoengine import (
    BooleanField,
    CASCADE,
    DateTimeField,
    Document,
    DO_NOTHING,
    ListField,
    ReferenceField,
    StringField,
)

from app.models.mongo.deprecated.skeleton import SkeletonModel
from app.models.mongo.user import UserModel


class AnalysisModel(Document):
    """
    Based on analysis tools（Published）Analysis of
    """
    id = StringField(primary_key=True)  # uuid
    is_trial = BooleanField(default=False)  # Analysis tool test run time，is_trial=True
    skeleton = ReferenceField(SkeletonModel, reverse_delete_rule=DO_NOTHING)    # DO_NOTHING
    user = ReferenceField(UserModel, reverse_delete_rule=CASCADE)   # The user of the tool:  CASCADE
    name = StringField()    # Analysis name，Non-tool names
    description = StringField()
    steps = ListField(StringField())  # [`AnalysisStep`.id]
    state = StringField(default="INCOMPLETED")  # INCOMPLETED, COMPLETED
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
