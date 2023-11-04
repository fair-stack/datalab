# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:event_parameters
@time:2022/08/31
"""
from pydantic import BaseModel
from typing import List, Optional
from app.core.config import settings


class S3Data(BaseModel):
    bucket: str
    object_name: str
    file_type: Optional[str] = None


class S3LoadData(BaseModel):
    bucket: str
    object_name: str
    file_type: str


class LaunchSchema(BaseModel):
    package_dir: str
    file_name: str
    function_name: str


class GatewayTaskData(BaseModel):
    load_data: Optional[List[S3LoadData]] = None
    upload_data: Optional[List[S3Data]] = None


class EventParameters(BaseModel):
    lab_id: str
    task_id: str
    gateway_task_data: GatewayTaskData
    datalab_launch: LaunchSchema
    parameters: dict
    memory_output: Optional[None] = None


class PythonTaskS3Data(BaseModel):
    load_data: Optional[List[S3Data]]
    upload_data: Optional[List[S3Data]]


class PythonLaunchParameters(BaseModel):
    package_dir: str
    file_name: str
    function_name: str


class PythonFunctionMemoryOutPut(BaseModel):
    pass


class DataLabDataBaseParameters(BaseModel):
    REDIS_HOST:  str = settings.REDIS_HOST
    MONGO_HOST:  str = settings.MONGODB_SERVER
    MINIO_URL:  str = settings.MINIO_URL
    MINIO__ACCESS_KEY:  str = settings.MINIO__ACCESS_KEY
    MINIO_SECRET_KEY:  str = settings.MINIO_SECRET_KEY


class FaaSEventRequestBody(BaseModel):
    lab_id: str
    task_id: str
    user_id: str
    gateway_task_data: PythonTaskS3Data
    datalab_launch: PythonLaunchParameters
    parameters: dict
    memory_output: Optional[None] = None
    datalab_env = DataLabDataBaseParameters()



#
# {'lab_id': 'cd2c7461bc6f4775b03cb16741',
#  'task_id': '4ba2c0f945744387a4cd98159f',
#  'gateway_task_data': {'load_data': [], 'upload_data': []},
#  'datalab_launch': {'package_dir': '/home/app/function', 'file_name': 'main.py', 'function_name': 'add'},
#  'parameters': {'x': 1374, 'y': 864},
#  'memory_output': [],
#  'user_id': '0993bc4a65fa4d638dcdcf44030f7194'}
#
