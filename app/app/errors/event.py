# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:event
@time:2022/11/14
"""


class LabEventException(Exception):
    def __init__(self, message: str):
        self.message = f"{message}"

    def __str__(self):
        return self.message


class LabEventTypeException(Exception):
    def __init__(self, message: str, event_type: str):
        self.message = f"{event_type}: {message}"

    def __str__(self):
        return self.message



