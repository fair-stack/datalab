from datetime import datetime

from mongoengine import (
    BooleanField,
    CASCADE,
    DateTimeField,
    DictField,
    Document,
    DO_NOTHING,
    ListField,
    ReferenceField,
    StringField,
)

from .skeleton2 import SkeletonModel2
from .user import UserModel


class AnalysisModel2(Document):
    """
    Based on analysis tools（Published）Analysis of
    """
    id = StringField(primary_key=True)  # uuid
    is_trial = BooleanField(default=False)  # Analysis tool test run time，is_trial=True
    skeleton = ReferenceField(SkeletonModel2, reverse_delete_rule=DO_NOTHING)    # DO_NOTHING
    user = ReferenceField(UserModel, reverse_delete_rule=CASCADE)   # The user of the tool:  CASCADE
    name = StringField()    # Analysis name，Non-tool names
    description = StringField()
    dag = ListField(DictField(), required=True)     # Skeleton.dag
    inputs_config = DictField()     # Skeleton.inputs_config
    outputs_config = DictField()    # Skeleton.outputs_config
    inputs = ListField(DictField(), default=[])     # Skeleton.inputs
    outputs = ListField(DictField(), default=[])    # Skeleton.outputs
    state = StringField(default="READY")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
