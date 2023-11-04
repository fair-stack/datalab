from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class CompoundStepCreateSchema(BaseModel):
    skeleton: str
    name: str
    description: Optional[str]
    instruction: Optional[str]


class CompoundStepSchema(BaseModel):
    id: str
    skeleton: str
    name: str
    description: Optional[str]
    instruction: Optional[str]
    multitask_mode: str
    elements: Optional[List[Dict]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class CompoundStepUpdateSchema(BaseModel):
    name: Optional[str]
    description: Optional[str]
    instruction: Optional[str]
    multitask_mode: Optional[str]


