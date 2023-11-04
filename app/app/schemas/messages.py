# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:messages
@time:2022/11/16
"""
from pydantic import BaseModel
from typing import Optional


class MessagesSchema(BaseModel):
    id: str
    user: str
    from_user: Optional[str]
    title: str
    content: Optional[str]
    messages_source: str
    unread: bool
    creat_time: str
    read_time: Optional[str]
    operation_type: bool = True
    operation: bool = False


