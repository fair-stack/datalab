from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.schemas.tool_source import InputParam, OutputData


class CompoundStepElementCreateSchema(BaseModel):
    type: str   # CompoundStepElementTypes
    name: str
    src_id: str
    skeleton_id: str
    compoundstep_id: str
    loc_index: int = -1     # The target of the element/Current location


class CompoundStepElementInputParamSchema(InputParam):
    """
    data: experiment In the task At execution time，Input written by the frontend
    depend_on: {
        task_id: xx,
        output_name: xx
    }
    """
    data: Any   # file/file，for Dict
    display_name: Optional[str]
    depend_on: Optional[Dict[str, Any]]
    default_data_mode: Optional[str]


class CompoundStepElementOutputDataSchema(OutputData):
    """
    data: experiment In the task After successful execution，Output written by the frontend
    depended_by: [
        {
            task_id: xx,
            input_name: xx
        }
    ]
    """
    data: Any   # file/file，for Dict
    depended_by: Optional[List[Dict[str, Any]]]


class CompoundStepElementSchema(BaseModel):
    id: str
    skeleton: str
    compoundstep: str
    type: str
    name: str
    src_id: str
    derived_from_src_id: Optional[str]
    derived_from_src_name: Optional[str]
    derived_from_output_name: Optional[str]
    src_experiment: Optional[str]
    src_tool: Optional[str]
    inputs: Optional[List[CompoundStepElementInputParamSchema]]
    outputs: Optional[List[CompoundStepElementOutputDataSchema]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

