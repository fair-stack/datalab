from datetime import datetime

from mongoengine import (
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

from app.models.mongo.deprecated.skeleton import SkeletonModel
from app.models.mongo.deprecated.compoundstep import CompoundStepModel

from app.models.mongo.experiment import ExperimentModel
from app.models.mongo.tool_source import InputParam, OutputData, XmlToolSourceModel

CompoundStepElementInputParam_DEFAULT_DATA_MODES = ("NO_DEFAULT", "DEPENDENCY", "DEFAULT_DATA")
CompoundStepElementTypes = ("TASK", "FILE", "DIR", "MEMORY")


class CompoundStepElementInputParam(InputParam):
    """
    data: experiment In the task At execution time，Input written by the frontend
    depend_on: {
        task_id: xx,
        output_name: xx
    }

    default_data_mode: Default data schema， Controls whether the Experiment The data I brought（non InputParam Inside of `default`）
        - Input parameter categories （According to `type`）：
            - File type：'dir', 'file'
            - Numeric： 'boolean','multi_select', 'number', 'select', 'text'
        - Each category，Has the following data schema：
            - File type： 1, no default data（User upload）， 2Use default data（ref original task Dependency）
            - Numeric： 1, no default data（User choice）， 2Use default data（Experiment I brought the input here `data`）
        - Add CompoundStepElement when，Initialization `default_data_mode` The strategy is as follows：
            - File type：
                - 1： Dependency（`depend_on` Is empty）
                - 2： Dependency（`depend_on` Is empty，Dependency Skeleton.CompoundStep；The error judgment logic is placed in Skeleton Test run）
            - Numeric：
                - 1： No default data，That is, not using Experiment The data I brought
        - If the setter changes the mode，Saves the user's Settings
        - For users of analytics tools：
            - File type： 1： You have to upload it yourself；      2： Dependency，Cannot upload（Dependency，Dependency，You get an error）
            - Data values： 1： Users have to fill it out themselves；  2：Use the default experimental values，But the user can still change it
        - Corresponding field value：
            - File type：  1： NO_DEFAULT,  2.DEPENDENCY
            - File type：  1： NO_DEFAULT,  2.DEFAULT_DATA
    """
    data = DynamicField()
    display_name = StringField()
    depend_on = DictField()
    default_data_mode = StringField(required=True, choices=CompoundStepElementInputParam_DEFAULT_DATA_MODES)


class CompoundStepElementOutputData(OutputData):
    """
    data: experiment In the task After successful execution，Output written by the frontend
    depended_by: [
        {
            task_id: xx,
            input_name: xx
        }
    ]
    """
    data = DynamicField()   #
    depended_by = ListField(DictField(), default=[])


class CompoundStepElementModel(Document):
    id = StringField(primary_key=True)  # <skeleton>_<comp>_<src>
    skeleton = ReferenceField(SkeletonModel, reverse_delete_rule=CASCADE, required=True)
    compoundstep = ReferenceField(CompoundStepModel, reverse_delete_rule=CASCADE, required=True)
    type = StringField(required=True)       # CompoundStepElementTypes
    name = StringField(required=True)
    src_id = StringField(required=True)     # task_id or data_id
    derived_from_src_id = StringField()    # Only for DATA
    derived_from_src_name = StringField()    # Only for DATA
    derived_from_output_name = StringField()    # Only for DATA
    src_experiment = ReferenceField(ExperimentModel, reverse_delete_rule=DO_NOTHING)
    src_tool = ReferenceField(XmlToolSourceModel, reverse_delete_rule=DO_NOTHING)
    inputs = ListField(DictField())     # Only for TASK
    outputs = ListField(DictField())    # Only for TASK
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
