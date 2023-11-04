# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:visualization
@time:2023/03/21
"""
from pydantic import BaseModel
from typing import Optional, Dict, List


class VisualizationDataInCrate(BaseModel):
    data_id: str
    component_id: str


class VisualizationComponentsResponse(BaseModel):
    name: Optional[str] = None
    data: Optional[str] = None
    installed: bool = False
    other: Optional[List[Dict]] = None
    id: str = None
    status: int = 200
