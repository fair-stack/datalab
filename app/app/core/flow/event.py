# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:event
@time:2022/11/14
"""
from app.app.core.config import settings
from app.app.errors.event import LabEventTypeException


class LabEvent:
    def __init__(self, publisher, event_type: str, tools_id: str, step_id: str):
        self.publisher = publisher
        if event_type not in settings.FLOW_EVENT_TYPES:
            raise LabEventTypeException(event_type, "Unrecognized event")
        self.event_type = event_type
        publisher.lpush(step_id, event_type)


