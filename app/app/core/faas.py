# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:faas
@time:2023/02/03
"""
import os
import pickle
import requests
from fastapi import status
from fastapi.responses import JSONResponse
from app.utils.middleware_util import get_s3_client
from app.core.config import settings
from app.utils.middleware_util import get_redis_con
from app.utils.middleware_util import get_s3_client
from app.schemas.event_parameters import S3Data, PythonLaunchParameters, FaaSEventRequestBody
from app.models.mongo import ToolTaskModel, XmlToolSourceModel, ComponentInstance, DataFileSystem

MEMORY_OUTPUT_LANGUAGE = ['python3', 'python3-debian']


class FaaSEventGenerator:
    def __init__(self, user_id: str, function_name: str, **event_params):
        """
        Event generator for Function as a Service
        :param user_id: The user who initiated the calculation
        :param function_name: Function of initiating a calculation
        """
        self.user_id = user_id
        self.component = XmlToolSourceModel.objects(name=function_name).first()
        self.component_instance = ComponentInstance.objects(base_id=self.component.id).first()
        self.function_name = function_name
        self.user_id = user_id
        assert event_params.get('task_id') and event_params.get('lab_id'),\
            f"This schedule failed.，Metadata information is lost: {'Operator taskIdlost' if event_params.get('lab_id') else 'ExperimentIdlost'}"
        self.lab_id = event_params['lab_id']
        self.task_id = event_params['task_id']
        self.component_name = function_name
        self.parameters = event_params
        self.component_metadata = XmlToolSourceModel.objects(folder_name=self.component_name).first()
        self.component_instance = ComponentInstance.objects(base_id=self.component_metadata.id).first()
        self.inputs_keys = [_['name'] for _ in self.component_metadata.inputs]
        self.outputs_keys = [_['name'] for _ in self.component_metadata.outputs]
        self.parameters.pop('lab_id')
        self.parameters.pop('task_id')
        self.load_type = {'file', 'dir'}
        self.con = get_redis_con(5)
        self.oss_client = get_s3_client()
        self._memory_output = None

    def s3_parameter(self, meta_input):
        pass


    def generator_inputs(self):
        print(self.inputs_keys)
        print(self.component_metadata.inputs)

    # def package_parameters(self):
    #     load_data = self.generator_inputs
    #     upload_data = self.upload_parameters
    #     gateway_data = GatewayTaskData(load_data=load_data,
    #                                    upload_data=upload_data)
    #     "self.component_metadata.folder_path"
    #     launch_ins = LaunchSchema(package_dir="/home/app/function",
    #                               file_name=self.component_metadata.executable,
    #                               function_name=self.component_metadata.command)
    #
    #     _parameters = EventParameters(lab_id=self.lab_id,
    #                                   task_id=self.task_id,
    #                                   datalab_launch=launch_ins,
    #                                   parameters=self.parameters,
    #                                   gateway_task_data=gateway_data
    #                                   ).dict()
    #     _parameters['user_id'] = self.user_id
    #     if self._memory_output is not None:
    #         _parameters['memory_output'] = self._memory_output
    #     return _parameters


if __name__ == '__main__':
    event_data = {'lab_id': 'cd2c7461bc6f4775b03cb16741',
                  'task_id': '4ba2c0f945744387a4cd98159f',
                  'gateway_task_data': {'load_data': [], 'upload_data': []},
                  'datalab_launch':
                      {'package_dir': '/home/app/function',
                       'file_name': 'main.py',
                       'function_name': 'add'},
                  'parameters': {'x': 1374, 'y': 864},
                  'memory_output': [],
                  'user_id': '0993bc4a65fa4d638dcdcf44030f7194'}

    test_data = {"task_id": "4ba2c0f945744387a4cd98159f",
                 "lab_id": "cd2c7461bc6f4775b03cb16741",
                 "x": {"id": "cd2c7461bc6f4775b03cb16741_40c8375934af4c94a155347768"}, "y": 864}
