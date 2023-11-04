# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:microservices
@time:2023/05/25
"""
from pydantic import BaseModel, AnyUrl
from typing import Optional


class MicroservicesSchemas(BaseModel):
    id: str
    name: str
    port: int
    host: AnyUrl
    description: Optional[str] = None
    upstream_id: str
    router_id: str
    router: str
    user: str
    integration_at: str
    modify_at: str
    state: str
    deleted: bool
