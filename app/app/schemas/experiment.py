from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

from app.utils.common import generate_uuid


class TrialExperimentSchema(BaseModel):
    trial_tool_id: str
    name: str
    description: Optional[str]


class ExperimentBaseSchema(BaseModel):
    is_trial: Optional[bool] = False
    trial_tool_id: Optional[str]
    name: str
    description: Optional[str]


class ExperimentUpdateSchema(BaseModel):
    name: Optional[str]
    description: Optional[str]


class ExperimentInDBSchema(ExperimentBaseSchema):
    id: Optional[str]
    is_shared: Optional[bool]
    shared_from_experiment: Optional[str]
    user: Optional[str]
    tasks: Optional[List[str]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class ExperimentBatchDeleteSchema(BaseModel):
    ids: Optional[List[str]]


def convertSchemaExptBaseToExptInDB(expt: ExperimentBaseSchema, user: str) -> ExperimentInDBSchema:
    exptInDBSchema = ExperimentInDBSchema(**expt.dict())
    exptInDBSchema.id = generate_uuid(length=26)
    exptInDBSchema.user = user
    exptInDBSchema.created_at = datetime.utcnow()
    exptInDBSchema.updated_at = datetime.utcnow()
    return exptInDBSchema


def convertSchemaTrialExptToExptInDB(trial: TrialExperimentSchema, user: str) -> ExperimentInDBSchema:
    exptInDBSchema = ExperimentInDBSchema(**trial.dict())
    exptInDBSchema.id = generate_uuid(length=26)
    exptInDBSchema.user = user
    # NOTE: is_trial = True
    exptInDBSchema.is_trial = True
    exptInDBSchema.created_at = datetime.utcnow()
    exptInDBSchema.updated_at = datetime.utcnow()
    return exptInDBSchema
