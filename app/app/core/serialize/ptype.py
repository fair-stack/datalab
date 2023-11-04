# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:ptype
@time:2023/02/01
"""
import pandas as pd
import numpy as np
from pydantic import BaseModel
from typing import Any


USED = [str, int, float, set, list, tuple, dict, bool, pd.DataFrame, np.ndarray]


class PythonSerializeResultResponse(BaseModel):
    language: str = "Python"
    type: str
    frontend: str
    data: Any
    serialize: str


class PythonObjectSerialize:

    @staticmethod
    def from_int(data: int):
        return PythonSerializeResultResponse(data=str(data), type="int", frontend="number", serialize=str(data)).dict()

    @staticmethod
    def from_float(data: float):
        return PythonSerializeResultResponse(data=str(data), type="float", frontend="number", serialize=str(data)).dict()

    @staticmethod
    def from_str(data: str):
        return PythonSerializeResultResponse(data=data, type="str", frontend="text", serialize=str(data)).dict()

    @staticmethod
    def from_list(data: list):
        return PythonSerializeResultResponse(data=str(data), type="list", frontend="object", serialize=str(data)).dict()

    @staticmethod
    def from_bool(data: bool):
        return PythonSerializeResultResponse(data=str(data), type="bool", frontend="boolean", serialize=str(data)).dict()

    @staticmethod
    def from_dict(data: bool):
        return PythonSerializeResultResponse(data=str(data), type="dict", frontend="object", serialize=str(data)).dict()

    @staticmethod
    def from_tuple(data: bool):
        return PythonSerializeResultResponse(data=str(data), type="tuple", frontend="object", serialize=str(data)).dict()

    @staticmethod
    def from_set(data: set):
        return PythonSerializeResultResponse(data=str(data), type="set", frontend="object", serialize=str(data)).dict()

    @staticmethod
    def from_dataframe(data: pd.DataFrame):
        return PythonSerializeResultResponse(data=str(data), type="pandas.DataFrame", frontend="object",
                                             serialize=str(data)).dict()

    @staticmethod
    def from_ndarray(data: np.ndarray):
        return PythonSerializeResultResponse(data=str(data), type="numpy.ndarray", frontend="object",
                                             serialize=str(data)).dict()

    @staticmethod
    def from_object(data: Any):
        return PythonSerializeResultResponse(data=str(data), type=str(data.__class__.__name__), frontend="object",
                                             serialize=str(data)).dict()


PYTHON_OBJECT_FRONTEND_MAP = {"int": PythonObjectSerialize.from_int,
                              "str": PythonObjectSerialize.from_str,
                              "bool": PythonObjectSerialize.from_bool,
                              "float": PythonObjectSerialize.from_float,
                              "list": PythonObjectSerialize.from_list,
                              "dict": PythonObjectSerialize.from_dict,
                              "tuple": PythonObjectSerialize.from_tuple,
                              "set": PythonObjectSerialize.from_set,
                              "DataFrame": PythonObjectSerialize.from_dataframe,
                              "ndarray": PythonObjectSerialize.from_ndarray,
                              "object": PythonObjectSerialize.from_object
                              }


def frontend_map(data: Any, data_id: str):
    frontend_type_function = PYTHON_OBJECT_FRONTEND_MAP.get(data.__class__.__name__)
    if frontend_type_function is None:
        frontend_data = PythonObjectSerialize.from_object(data)
    else:
        frontend_data = frontend_type_function(data)
    frontend_data['id'] = data_id
    return frontend_data
