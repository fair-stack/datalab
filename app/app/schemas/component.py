# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:component
@time:2022/08/23
"""
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List, Dict, Union


class ComponentRunType(BaseModel):
    synchronous = "synchronous"
    asynchronous = "asynchronous"


class AsynchronousServiceResponse(BaseModel):
    msg: str
    data: dict


class SynchronousServiceResponse(BaseModel):
    msg: str
    data: Union[List, Dict, str]
    serialization: bool


class ComponentInstanceSchema(BaseModel):
    id: str
    component_name: str
    synchronous_uri: str
    asynchronous_uri: str
    image_name: str
    docker_file: Optional[str] = None
    uri_type: str
    serialization: Optional[bool] = None
    # compute/visualization
    component_type: str

