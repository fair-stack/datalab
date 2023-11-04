# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:images
@time:2022/08/11
"""
from pydantic import BaseModel


class ImagesSchema(BaseModel):
    id: str
    image_id: str
    image_short_id: str
    source_id: str
    source_name: str
    tags: str
    image_size: int
    from_user: str
    created_at: str

