# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:digital_asset
@time:2023/06/08
"""
from pydantic import BaseModel
from typing import Optional


class ExperimentsDigitalAssetsSchema(BaseModel):
    id: str
    name: str
    is_file: bool
    data_size: int
    data_path: str
    user: str
    description: Optional[str] = None
    file_extension: Optional[str] = None
    from_user: Optional[str] = None
    deleted: bool
    created_at: str
    updated_at: str
    parent: str
    project: Optional[str] = None
    task: Optional[str] = None
    typing: Optional[str] = None
    from_source: Optional[str] = None
