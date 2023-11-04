from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class RoleBaseSchema(BaseModel):
    id: str
    name: str
    is_innate: Optional[bool]
    is_default_role: Optional[bool]


class RoleSchema(BaseModel):
    id: str
    name: str
    permissions: Optional[List[Dict[str, Any]]]
    is_innate: Optional[bool]
    is_default_role: Optional[bool]
    creator: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class RoleCreateSchema(BaseModel):
    name: str
    is_default_role: Optional[bool] = False
    permissions: List[Dict[str, Any]]


class RoleUpdateSchema(BaseModel):
    name: Optional[str]
    is_default_role: Optional[bool] = False
    permissions: Optional[List[Dict[str, Any]]]
