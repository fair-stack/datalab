# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:gate
@time:2022/08/23
"""
import os
import requests
from fastapi import status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.utils.middleware_util import get_redis_con
from app.utils.middleware_util import get_s3_client
from app.schemas.event_parameters import EventParameters, LaunchSchema, GatewayTaskData, S3Data, S3LoadData
from app.models.mongo import ToolTaskModel, XmlToolSourceModel, ComponentInstance,  DataFileSystem
from app.models.mongo.public_data import PublicDataFileModel
from app.service.manager.task import ComputeTaskManager

Memory_OUTPUT_LANGUAGE = ['python']


def post_function(function_name: str, data: dict):
    """
    :param function_name:  Faas Function Service Name http:cloud-gateway/async-function/{function_name}
    :param data: Function service-->Component running parameters
    :return:
    """
    con = get_redis_con(5)
    task_id = data.get('task_id')
    lab_id = data.get('lab_id')
    con[task_id+'-task'] = "Start"
    con.lpush(task_id, "")
    assert task_id and lab_id, f"This schedule failed.，Metadata information is lost: {'Operator taskIdlost' if lab_id else 'ExperimentIdlost'}"
    url = f'{settings.ASYNC_FUNCTION_DOMAIN}{function_name}'
    res = requests.post(url, json=data,
                        headers={"X-Callback-Url": f"http://{settings.SERVER_HOST}/callback/{task_id}"})
    if res.status_code != 202:
        raise ModuleNotFoundError(f"|{function_name}| is not found")
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={
                            "msg": f"Component task {task_id} has been created",
                            "data": {"id": task_id}
                        }
                        )


def runtime_exec(function_name,
                 data: dict = None,
                 method: str = "GET"):
    url = f'{settings.FUNCTION_DOMAIN}{function_name}'
    serialization = False if function_name in ['jpgvis', 'pngvis'] else True
    if method == "POST":
        resp = requests.post(url,
                             data=data)
    else:
        resp = requests.get(url)
    if serialization:
        _serialization_data = resp.text.split('VISTOTAL')[0]
        _total = resp.text.split('VISTOTAL')[1]
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={
                                'data': eval(_serialization_data),
                                "serialization": True,
                                'msg': 'Success',
                                'total': int(_total)
                            })
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={'data': resp.text, "serialization": False, 'msg': 'Success'})


class PublishTask:
    def __init__(self, task_id, db=5):
        self.con = get_redis_con(db)
        self.task_id = task_id

    def write(self, _strings):
        self.con.rpush(self.task_id, _strings)

    def publisher(self, start_index: int):
        for _ in self.con.lrange(self.task_id, start_index, -1):
            yield _.decode()

    def pending(self):
        _data = self.con.lindex(self.task_id, -1)
        if _data is not None:
            return self.con.lindex(self.task_id, -1).decode()
        return ""

    @property
    def status(self):
        return self.con[self.task_id+'-task'].decode()


def split_object_name(file_name: str):
    if file_name.startswith('/'):
        return file_name, file_name[1:]
    return file_name, file_name


def check_object_exits(bucket_name: str, object_name: str, dst_name: str, client=None, redis_client=None,
                       lab_id: str = None):
    if client is None:
        client = get_s3_client()
    _split_object_name = object_name.split('/')
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
    if len(_split_object_name) > 1:
        try:
            redis_client[_split_object_name[0] + '-task'].decode()
        except KeyError:
            ...
        else:
            tool_task_object = ToolTaskModel.objects(id=_split_object_name[0]).first()
            if tool_task_object is not None:
                bucket_name = tool_task_object.experiment.id
                if not client.bucket_exists(bucket_name):
                    client.make_bucket(bucket_name)
            # else:
            #     ase = AnalysisStepElementModel.objects(id=_split_object_name[0]).first()
            #     bucket_name = ase.analysis.id
            #     if not client.bucket_exists(bucket_name):
            #         client.make_bucket(bucket_name)

    _objs = list(client.list_objects(bucket_name, object_name))
    if not _objs:
        _dfs = DataFileSystem.objects(lab_id=lab_id, name=object_name).first()
        if _dfs:
            bucket_name = lab_id
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
            object_name = _dfs.task_id + '/' + object_name
        else:

            _pdf = PublicDataFileModel.objects(data_path=object_name).first()
            if _pdf is not None:
                print("Public Data")
                return _pdf.datasets.id, object_name
            else:
                if os.path.isdir(dst_name):
                    for root, dirs, files in os.walk(dst_name):
                        for _file in files:
                            obj_abs = os.path.join(root, _file)
                            client.fput_object(bucket_name, obj_abs, obj_abs)
                else:
                    client.fput_object(bucket_name, object_name, dst_name)
    return bucket_name, object_name


class FunctionEvent:
    def __init__(self, user_id, function_name, outputs_point: str = None, **kwargs):
        self.outputs_point = outputs_point
        self.function_name = function_name
        self.user_id = user_id
        assert kwargs.get('task_id') and kwargs.get('lab_id'), f"This schedule failed.，Metadata information is lost: " \
                                                               f"{'Operator taskIdlost' if kwargs.get('lab_id') else 'ExperimentIdlost'}"
        self.lab_id = kwargs['lab_id']
        self.task_id = kwargs['task_id']
        self.component_name = function_name
        self.parameters = kwargs
        self.component_metadata = XmlToolSourceModel.objects(folder_name=self.component_name).first()
        # self.component_metadata = XmlToolSourceModel.objects(name=self.component_name).first()
        self.component_instance = ComponentInstance.objects(base_id=self.component_metadata.id).first()
        self.inputs_keys = [_['name'] for _ in self.component_metadata.inputs]
        self.outputs_keys = [_['name'] for _ in self.component_metadata.outputs]
        self.parameters.pop('lab_id')
        self.parameters.pop('task_id')
        self.load_type = {'file', 'dir'}
        self.con = get_redis_con(5)
        self.oss_client = get_s3_client()
        self._memory_output = None

    @property
    def upload_parameters(self):
        entity_list = list()
        memory_list = list()
        for _ in self.component_metadata.outputs:
            if _['format'] in Memory_OUTPUT_LANGUAGE:
                memory_list.append(_)
            else:
                entity_list.append(_)
        self.memory_output_data_parameters(memory_list)
        return self.s3_parameters(entity_list, self.lab_id)

    @property
    def load_parameters(self):
        print("load_parameters",self.component_metadata.inputs)
        return self.s3_parameters(self.component_metadata.inputs, bucket=self.user_id, type_check=True)

    def memory_output_data_parameters(self, data: list):
        self._memory_output = data

    def s3_parameters(self, data: list, bucket: str, type_check: bool = False):
        s3_data_list = list()
        for _ in data:
            value = self.parameters.get(_['name'])
            if type_check:
                if _['type'] == "datasets":
                    print("DEBUG-----"", value, _,)
                    s3_data_list.append(S3LoadData(
                        bucket=value['id'],
                        object_name=f'home/data_storage/storage_data/uploads_datasets_cache/{value["id"]}',
                        file_type="dir"
                    ))
                    self.parameters[_['name']] = f'home/data_storage/storage_data/uploads_datasets_cache/{value["id"]}'
                elif _['type'] == "List[datasets]":
                    _datasets_list = list()
                    for _datasets in value:
                        s3_data_list.append(S3LoadData(
                            bucket=_datasets['id'],
                            object_name=f'home/data_storage/storage_data/uploads_datasets_cache/{_datasets["id"]}',
                            file_type="dir"
                        ))
                        _datasets_list.append(f'home/data_storage/storage_data/uploads_datasets_cache/{_datasets["id"]}')
                    self.parameters[_['name']] = _datasets_list
                elif isinstance(value, dict):
                    self.parameters[_['name']] = value
                elif _['type'] in self.load_type and _['name'] not in self.outputs_keys:
                    dst_name, value = split_object_name(value)
                    self.parameters[_['name']] = value
                    bucket, value = check_object_exits(self.user_id, value, dst_name, redis_client=self.con,
                                                       lab_id=self.lab_id)
                    self.parameters[_['name']] = value
                    s3_data_list.append(
                        S3LoadData(
                            bucket=bucket,
                            object_name=value,
                            file_type=_['type']
                        )
                    )
            else:
                if _['type'] in ["file", "dir"]:
                    s3_data_list.append(
                        S3Data(
                            bucket=bucket,
                            object_name=value
                        )
                    )
        return s3_data_list

    @property
    def package_parameters(self):
        load_data = self.load_parameters
        upload_data = self.upload_parameters
        gateway_data = GatewayTaskData(load_data=load_data,
                                       upload_data=upload_data)
        "self.component_metadata.folder_path"
        launch_ins = LaunchSchema(package_dir="/home/app/function",
                                  file_name=self.component_metadata.executable,
                                  function_name=self.component_metadata.command)

        _parameters = EventParameters(lab_id=self.lab_id,
                                      task_id=self.task_id,
                                      datalab_launch=launch_ins,
                                      parameters=self.parameters,
                                      gateway_task_data=gateway_data
                                      ).dict()
        _parameters['user_id'] = self.user_id
        if self._memory_output is not None:
            _parameters['memory_output'] = self._memory_output
        return _parameters

    def start(self):
        self.con[self.task_id + '-task'] = "Start"
        self.con.lpush(self.task_id, "==== DataLab Start Function ====")

    def failed(self):
        self.con[self.task_id + '-task'] = "Failed"
        self.con.lpush(self.task_id, "==== DataLab Function Failed ====")

    def reaction(self, task_type: str):
        _task_queue_id = None
        if task_type == 'task':
            _task_queue_id = ComputeTaskManager.add_task(ToolTaskModel.objects(id=self.task_id).first(), self.user_id)
        self.start()
        _data = self.package_parameters
        datalab_env = dict()
        datalab_env['REDIS_HOST'] = settings.REDIS_HOST
        datalab_env['MONGO_HOST'] = settings.MONGODB_SERVER
        datalab_env['MINIO_URL'] = settings.MINIO_URL
        datalab_env['MINIO__ACCESS_KEY'] = settings.MINIO__ACCESS_KEY
        datalab_env['MINIO_SECRET_KEY'] = settings.MINIO_SECRET_KEY
        datalab_env['OUTPUTS_POINT'] = self.outputs_point
        _data['datalab_env'] = datalab_env
        res = requests.post(self.component_instance.asynchronous_uri,
                            json=_data,
                            headers={
                                "X-Callback-Url":
                                    f"http://{settings.SERVER_HOST}/api/components/callback/{_task_queue_id}"}
                            )
        self.con.close()
        if res.status_code != 202:
            raise ModuleNotFoundError(f"|{self.function_name}| is not found")
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": f"Component task {self.task_id} has been created",
                                     "data": {"id": self.task_id}})
