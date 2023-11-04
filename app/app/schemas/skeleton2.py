from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class Skeleton2CreateSchema(BaseModel):
    skeleton_renewed: Optional[str]
    experiment: str
    experiment_tasks: List[str]  # List[str] ---> List[Dict]
    experiment_tasks_datasets: List[Dict]
    name: Optional[str]
    description: Optional[str]
    introduction: Optional[str]
    dag: Optional[List[Dict]]


class Skeleton2Schema(BaseModel):
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
    name: Optional[str]
    description: Optional[str]
    introduction: Optional[str]
    logo: Optional[str]
    previews: Optional[List[str]]
    organization: Optional[str]
    developer: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    statement: Optional[str]
    dag: Optional[List[Dict]]
    inputs_config: Optional[Dict]
    outputs_config: Optional[Dict]
    inputs: Optional[List[Dict]]
    outputs: Optional[List[Dict]]
    state: str
    auditor: Optional[str]
    audit_opinion: Optional[str]
    category: Optional[str]
    is_online: Optional[bool]
    pageviews: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class Skeleton2BasicSchema(BaseModel):
    id: str
    version: Optional[str]
    version_meaning: Optional[str]
    user: str
    experiment: str
    name: Optional[str]
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


class Skeleton2UpdateSchema(BaseModel):
    dag: Optional[List[Dict]]
    inputs: Optional[List[Dict]]
    outputs: Optional[List[Dict]]
    inputs_config: Optional[Dict]
    outputs_config: Optional[Dict]
