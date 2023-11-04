from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class ToolTaskForSkeletonCreationSchema(BaseModel):
    task_id: str
    task_name: str
    description: Optional[str]
    tool: Optional[str]
    experiment: Optional[str]
    user: Optional[str]
    inputs: Optional[List[Dict[str, Any]]]
    outputs: Optional[List[Dict[str, Any]]]
    status: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    is_used: bool


class ToolTaskBaseSchema(BaseModel):
    id: str
    name: Optional[str]
    status: Optional[str]


class ToolTaskSchema(BaseModel):
    id: str
    name: Optional[str]
    description: Optional[str]
    tool: Optional[str]
    experiment: Optional[str]
    user: Optional[str]
    inputs: Optional[List[Dict[str, Any]]]
    outputs: Optional[List[Dict[str, Any]]]
    status: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class ToolTaskCreateSchema(BaseModel):
    """
    """
    experiment_id: str
    name: Optional[str]
    description: Optional[str]


class ToolTaskCreatedSchema(BaseModel):
    """
    """
    experiment_id: str
    tool_task_id: str


class ToolTaskUpdateSchema(BaseModel):
    name: Optional[str]
    description: Optional[str]
    tool_id: Optional[str]
    inputs: Optional[List[Dict[str, Any]]]
    outputs: Optional[List[Dict[str, Any]]]
    status: Optional[str]
