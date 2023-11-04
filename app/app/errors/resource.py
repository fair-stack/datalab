# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:resource
@time:2023/05/17
"""


class ResourceException(Exception):
    def __init__(self, message: str):
        self.message = f"{message}"

    def __str__(self):
        return self.message


class ResourceTransgressionException(ResourceException):
    pass


class ResourceRuleUnitException(ResourceException):
    pass


class ResourceUnDistributableException(ResourceException):
    pass
