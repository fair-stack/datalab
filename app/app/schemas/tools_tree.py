# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:tools_tree
@time:2022/10/12
"""
import uuid
import datetime
from pydantic import BaseModel


class ToolsTreeSchema(BaseModel):
    id: str = str(uuid.uuid4())
    name: str
    level: int
    parent: str = "root"


class ToolsTreeResponseSchema(BaseModel):
    id: str
    name: str
    level: int
    parent: str
    user: str
    created_at: str
    updated_at: str
