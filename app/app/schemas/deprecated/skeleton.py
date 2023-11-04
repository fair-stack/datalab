from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

from app.utils.common import generate_uuid


class SkeletonCreateSchema(BaseModel):
    skeleton_renewed: Optional[str]
    experiment: str
    experiment_tasks: List[str]  # List[str] ---> List[Dict]
    experiment_tasks_datasets: List[Dict]
    name: str
    description: Optional[str]
    introduction: Optional[str]


class SkeletonSchema(BaseModel):
    id: str
    skeleton_renewed: Optional[str]
    skeleton_renewed_origin: Optional[str]
    version: Optional[str]
    version_meaning: Optional[str]
    user: Optional[str]
    experiment: Optional[str]
    experiment_tasks: List[Dict]
    experiment_tasks_datasets: List[Dict]
    experiment_tasks_dependencies: List[Dict]
    name: str
    description: Optional[str]
    introduction: Optional[str]
    logo: Optional[str]
    compoundsteps: Optional[List[str]]
    state: str
    auditor: Optional[str]
    audit_opinion: Optional[str]
    category: Optional[str]
    is_online: Optional[bool]
    pageviews: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SkeletonBasicSchema(BaseModel):
    id: str
    version: Optional[str]
    version_meaning: Optional[str]
    user: str
    experiment: str
    name: str
    description: Optional[str]
    introduction: Optional[str]
    logo: Optional[str]
    state: str
    auditor: Optional[str]
    audit_opinion: Optional[str]
    category: Optional[str]
    is_online: Optional[bool]
    pageviews: Optional[int]
    created_at: str     # not Optional[datetime]
    updated_at: str     # not Optional[datetime]
