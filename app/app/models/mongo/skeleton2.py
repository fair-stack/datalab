from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    DO_NOTHING,
    IntField,
    ListField,
    NULLIFY,
    ReferenceField,
    StringField,
)

from .experiment import ExperimentModel
from .user import UserModel


# Not reviewed: UNAPPROVED / Under review: APPROVING / Approved by review: APPROVED / Failed to pass the audit: DISAPPROVED
SKELETON_STATES = ["UNAPPROVED", "APPROVING", "APPROVED", "DISAPPROVED"]
SKELETON_STATES_NOT_EDITABLE = ["APPROVING", "APPROVED"]    # Approved by review，Not editable


class SkeletonCategoryModel(Document):
    """
    Classification of Analysis Tools
    """
    id = StringField(primary_key=True)
    user = ReferenceField(UserModel, reverse_delete_rule=DO_NOTHING)
    name = StringField(unique=True, required=True)
    num = IntField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)


class SkeletonModel2(Document):
    """
    Analysis tools

    - Approved by review：
        - Automated launch，Available to other users； Meanwhile，The publisher of the tool is not allowed to edit again
        - If skeleton_renewed Not empty，I'm going to log off skeleton_renewed the
    """
    id = StringField(primary_key=True)
    skeleton_renewed = StringField()
    skeleton_renewed_origin = StringField()
    version = StringField(required=True)
    version_meaning = StringField()
    user = ReferenceField(UserModel, reverse_delete_rule=DO_NOTHING)
    experiment = ReferenceField(ExperimentModel, reverse_delete_rule=DO_NOTHING)
    name = StringField(default="")
    description = StringField(default="")
    introduction = StringField(default="")
    logo = StringField()
    previews = ListField(StringField())     # Cover image
    organization = StringField()
    developer = StringField()
    contact_name = StringField()
    contact_email = StringField()
    contact_phone = StringField()
    statement = StringField()
    experiment_tasks = ListField(DictField(required=True), required=True)
    experiment_tasks_datasets = ListField(DictField(required=True), required=True)  # TODO: rm
    dag = ListField(DictField(), default=[])     # New fields, For strings only dag logic， There is no data
    inputs_config = DictField()
    outputs_config = DictField()
    inputs = ListField(DictField(), default=[])     # New fields，Settings+data
    outputs = ListField(DictField(), default=[])    # New fields，Settings+data
    state = StringField(required=True, choices=SKELETON_STATES, default="UNAPPROVED")  # Approved by review，synchronization
    auditor = ReferenceField(UserModel, reverse_delete_rule=DO_NOTHING)
    audit_opinion = StringField()
    category = ReferenceField(SkeletonCategoryModel, reverse_delete_rule=NULLIFY)
    is_online = BooleanField(default=False)  # Only is_online = False， Before you can delete it；
    pageviews = IntField(default=0)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
