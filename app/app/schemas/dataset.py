from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DatasetBaseSchema(BaseModel):
    id: Optional[str] = None
    name: str
    is_file: bool   # file, dir
    file_extension: Optional[str]
    data_size: Optional[int]
    user: Optional[str]
    description: Optional[str] = None
    from_source: Optional[str]
    from_user: Optional[str]    # Sharer
    deleted: Optional[bool]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class DatasetUpdateSchema(BaseModel):
    description: Optional[str] = None


class DatasetV2Schema(BaseModel):
    id: str
    name: str
    is_file: bool
    is_dir: bool
    store_name: str
    data_size: Optional[int]
    data_path: str
    user: str
    description: Optional[str] = None
    from_source: str
    from_user: Optional[str] = None
    deleted: bool
    created_at: str
    updated_at: str
    data_type: str
    storage_service: str
    file_extension: Optional[str]
    alias_name: Optional[str]
    parent: str
    child: list
    deps: int
    lab_id: str = None
    task_id: str = None


class DatasetsListResponseSchema(BaseModel):
    id: str
    name: str
    doi: Optional[str] = None
    cstr: Optional[str] = None
    description: Optional[str] = None
    source: str
    files_total: Optional[int] = 0
