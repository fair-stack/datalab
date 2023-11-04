# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:notebook
@time:2023/02/21
"""
from pydantic import BaseModel
from typing import Optional


class NoteBookProjectSchemas(BaseModel):
    id: str
    name: str
    create_at: str
    update_at: str
    description: Optional[str] = None
    user: str
    notebook_nums: int
    language: str
