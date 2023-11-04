from datetime import datetime

from mongoengine import (
    BooleanField,
    CASCADE,
    DateTimeField,
    DictField,
    Document,
    DO_NOTHING,
    DynamicField,
    ListField,
    ReferenceField,
    StringField,
)

from app.models.mongo.deprecated.analysis import AnalysisModel
from app.models.mongo.deprecated.analysis_step import AnalysisStepModel
from app.models.mongo.deprecated.compoundstep_element import CompoundStepElementModel

from app.models.mongo.tool_source import XmlToolSourceModel


class AnalysisStepElementModel(Document):
    """
    Analyze the elements within a step（Be born out of CompoundStepElement）， Similar to Experiment within task
    """
    id = StringField(primary_key=True)  # <analysis>_<analysis_step>_<src>, Among them src It's an analysis tool Element When created，Based on (task the `id`, or data the `_id`）
    compoundstep_element = ReferenceField(CompoundStepElementModel, reverse_delete_rule=DO_NOTHING, required=True)
    analysis = ReferenceField(AnalysisModel, reverse_delete_rule=CASCADE, required=True)
    analysis_step = ReferenceField(AnalysisStepModel, reverse_delete_rule=CASCADE, required=True)
    type = StringField(required=True)           # TASK / FILE / DIR / MEMORY
    name = StringField(required=True)
    src_id = StringField(required=True)         # Analysis tools Element When created，Based on (task the `id`, or data the `_id`）
    derived_from_src_id = StringField()         # type = FILE/DIR/MEMORY when： Must have
    derived_from_src_name = StringField()       # type = FILE/DIR/MEMORY when： Must have
    derived_from_output_name = StringField()    # type = FILE/DIR/MEMORY when： Must have
    data = DynamicField()                       # type = FILE/DIR/MEMORY when： Must have，the Analysis Data
    src_tool = ReferenceField(XmlToolSourceModel, reverse_delete_rule=DO_NOTHING)   # type=TASK when: Must have
    inputs = ListField(DictField())     # type=TASK when: Must have
    outputs = ListField(DictField())    # type=TASK when: Must have, when（when), outputs=[]
    is_selected = BooleanField(required=True, default=True)     # type=TASK when: Must have;  According to AnalysisStepModel.multitask_mode， User pair Element Make choices（Select all, single, multiple）after，the True
    state = StringField(required=True, default="UNUSED")        # logo：traversal Skeleton.CompoundStep.elements when，the Element the AnalysisStepElement
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
