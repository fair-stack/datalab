# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:cache_file
@time:2022/11/02
"""
from typing import Optional
from dataclasses import dataclass
from dataclasses import asdict


@dataclass
class CacheFileDataClass:
    id: str
    name: str
    is_file: int
    store_name: str
    data_size: Optional[int]
    data_path: Optional[str]
    from_source: Optional[str]
    deleted: Optional[bool]
    created_at: Optional[str]
    updated_at: Optional[str]
    data_type: Optional[str]
    data_type: str
    alias_name: str
    parent: str
    child: str
    size: int
    is_dir: int
    deps: int
    lab_id: Optional[str]
    task_id: Optional[str]
    file_extension: Optional[str] = ""
    user: Optional[str] = ""
    description: Optional[str] = ""
    from_user: Optional[str] = ""

    def to_dict(self):
        base_dict = asdict(self)
        base_dict['child'] = str(base_dict['child'])
        return base_dict
