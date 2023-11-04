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

from app.models.mongo.experiment import ExperimentModel
from app.models.mongo.user import UserModel

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
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)


# Deprecated
class SkeletonModel(Document):
    """
    Deprecated

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
    name = StringField(required=True)
    description = StringField(default="")
    introduction = StringField(default="")
    logo = StringField()
    experiment_tasks = ListField(DictField(required=True), required=True)
    experiment_tasks_datasets = ListField(DictField(required=True), required=True)
    experiment_tasks_dependencies = ListField(DictField(required=True), required=True)
    compoundsteps = ListField(StringField(required=True), default=[])
    state = StringField(required=True, choices=SKELETON_STATES, default="UNAPPROVED")   # Approved by review，synchronization
    auditor = ReferenceField(UserModel, reverse_delete_rule=DO_NOTHING)
    audit_opinion = StringField()
    category = ReferenceField(SkeletonCategoryModel, reverse_delete_rule=NULLIFY)
    is_online = BooleanField(default=False)     # Only is_online = False， Before you can delete it；
    pageviews = IntField(default=0)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
