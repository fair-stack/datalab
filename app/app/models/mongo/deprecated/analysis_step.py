from datetime import datetime

from mongoengine import (
    CASCADE,
    DateTimeField,
    Document,
    DO_NOTHING,
    ListField,
    ReferenceField,
    StringField,
)

from app.models.mongo.deprecated.analysis import AnalysisModel
from app.models.mongo.deprecated.compoundstep import CompoundStepModel

CompoundStepElementInputParam_DEFAULT_DATA_MODES = ("NO_DEFAULT", "DEPENDENCY", "DEFAULT_DATA")


class AnalysisStepModel(Document):
    """
    Analysis steps（Born out of analytical tools CompoundStep）
    """
    id = StringField(primary_key=True)
    compoundstep = ReferenceField(CompoundStepModel, reverse_delete_rule=DO_NOTHING)
    analysis = ReferenceField(AnalysisModel, reverse_delete_rule=CASCADE)
    name = StringField()
    description = StringField()
    instruction = StringField()
    multitask_mode = StringField(required=True, default="ALL")   # （Set when publishing tools，User not adjustable）All tasks are executed： ALL / Select a task to execute（Single selection）： SELECT / Select a task to execute（Single selection）：MULTI_SELECT
    elements = ListField(StringField())     # [AnalysisStepElement.id]
    state = StringField(default="READY")  # READY, SUCCESS, ERROR, PENDING
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
