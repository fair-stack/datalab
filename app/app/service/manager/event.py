# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:event
@time:2023/05/12
"""
import sys
from aioredis import Redis
sys.path.append('/Users/wuzhaochen/Desktop/workspace/datalab/app')
import requests
from datetime import datetime
from pydantic import BaseModel
from typing import Any, Optional, Union, List
from mongoengine.errors import MongoEngineException
from app.core.config import settings
from app.service.manager.task import ComputeTaskManager
from app.utils.common import generate_uuid
from app.utils.middleware_util import get_redis_con
from app.models.mongo.public_data import PublicDatasetModel, PublicDataFileModel
from app.models.mongo import UserModel, TaskQueueModel, XmlToolSourceModel, DataFileSystem, ComponentInstance, ToolTaskModel
from app.models.mongo import AnalysisModel2

class Parameter:

    def structure(self):
        raise NotImplementedError


class TextParameter(Parameter):
    def __init__(self, key: str, data: str):
        self.key = key
        self.data = data

    def structure(self):
        return {self.key: str(self.data)}


class IntParameter(Parameter):
    def __init__(self, key: str, data: Union[str, int, bool]):
        self.key = key
        self.data = data

    def structure(self):
        return {self.key: int(self.data)}


class DecimalParameter(Parameter):
    def __init__(self, key: str, data: Union[str, int, bool]):
        self.key = key
        self.data = data

    def structure(self):
        return {self.key: float(self.data)}


class BooleanParameter(Parameter):
    def __init__(self, key: str, data: Union[str, int, bool]):
        self.key = key
        self.data = data

    def structure(self):
        if not isinstance(self.data, bool):
            if self.data == "true":
                self.data = True
            elif self.data == "TRUE":
                self.data = True
            else:
                self.data = False
        return {self.key: self.data}


class FileParameter(Parameter):
    def __init__(self, key: str, file_id: str):
        self.key = key
        self.file_id = file_id

    def structure(self):
        element = dict()
        print("structure", self.key, self.file_id)
        file_id = self.file_id if isinstance(self.file_id, str) else self.file_id.get("id")
        _model = DataFileSystem.objects(id=file_id).first()
        if _model is None:
            _model = PublicDataFileModel.objects(id=file_id).first()
            try:
                bucket = _model.datasets.id
            except:
                bucket = "ca5bd4a0c469467393959fc020"
        else:
            bucket = _model.user.id

        _object_name = _model.data_path
        _schema = EntityObjectStorageSchema(bucket=bucket,
                                            object_name=_object_name[1:] if _object_name[0] == '/' else _object_name,
                                            file_type="file"
                                            )
        element[self.key] = _object_name
        return element, _schema


class DirParameter(Parameter):
    def __init__(self, key: str, file_id: str):
        self.key = key
        self.file_id = file_id

    def structure(self):
        element = dict()
        file_id = self.file_id if isinstance(self.file_id, str) else self.file_id.get("id")
        print(file_id)
        _model = DataFileSystem.objects(id=file_id).first()
        _object_name = _model.data_path
        _schema = EntityObjectStorageSchema(bucket=_model.user.id,
                                            object_name=_object_name[1:] if _object_name[0] == '/' else _object_name,
                                            file_type="dir"
                                            )
        element[self.key] = _object_name
        return element, _schema


class DatasetsParameter(Parameter):
    def __init__(self, key: str, datasets_id: str):
        self.key = key
        self.datasets_id = datasets_id

    def structure(self):
        element = dict()
        _model = PublicDataFileModel.objects(id=self.datasets_id).first()
        _object_name = "home/data_storage/storage_data/uploads_datasets_cache/" + _model.id
        _schema = EntityObjectStorageSchema(bucket=_model.id,
                                            object_name=_object_name,
                                            file_type="dir"
                                            )
        element[self.key] = _object_name
        return element, _schema


class MemoryParameter(Parameter):
    def __init__(self, key: str, object_id: str):
        self.key = key
        self.object_id = object_id

    def structure(self):
        element = dict()
        element[self.key] = self.object_id
        return element


class NestingParameter(Parameter):
    def __init__(self, key: str, frond_data: Any, expression: str):
        self.key = key
        self.frond_data = frond_data
        self.expression = expression

    def structure(self):
        _list = list()
        _schemas = list()
        if self.expression == "List[datasets]":
            for i in self.frond_data:
                _parma, _upload = DatasetsParameter(self.key, i['id']).structure()
                _schemas.append(_upload)
                _list.append(_parma[self.key])
        element = dict()
        element[self.key] = _list
        return element, _schemas


class EventParameter:

    def __init__(self, type_string: str, key: str, frond_data: Any, *args, **kwargs):
        self._type = type_string
        self.key = key
        self.frond_data = frond_data
        self.args = args
        self.kwargs = kwargs
        self.parameter_isinstance: Optional[Parameter] = None
        self.init_isinstance()

    def init_isinstance(self):
        if self._type == "text":
            self.parameter_isinstance = TextParameter(self.key, self.frond_data)
        elif self._type == "number":
            if isinstance(self.frond_data, str):
                if "." in self.frond_data:
                    self.parameter_isinstance = DecimalParameter(self.key, self.frond_data)
                else:
                    self.parameter_isinstance = IntParameter(self.key, self.frond_data)
            elif isinstance(self.frond_data, int):
                self.parameter_isinstance = IntParameter(self.key, self.frond_data)
            else:
                self.parameter_isinstance = DecimalParameter(self.key, self.frond_data)
        elif self._type == "boolean":
            self.parameter_isinstance = BooleanParameter(self.key, self.frond_data)
        elif self._type == "file":
            self.parameter_isinstance = FileParameter(self.key, self.frond_data)
        elif self._type == "dir":
            print(self.key, self.frond_data)
            self.parameter_isinstance = DirParameter(self.key, self.frond_data)
        elif self._type == "datasets":
            self.parameter_isinstance = DatasetsParameter(self.key, self.frond_data['id'])
        elif self._type == "object":
            self.parameter_isinstance = MemoryParameter(self.key, self.frond_data)
        elif "[" in self._type and "]" in self._type:
            self.parameter_isinstance = NestingParameter(self.key, self.frond_data, self._type)

    def get_element(self) -> dict:
        return self.parameter_isinstance.structure()


class EntityObjectStorageSchema(BaseModel):
    bucket: str
    object_name: str
    file_type: Optional[str] = None


class PhysicalTransmissionSchema(BaseModel):
    load_data: Optional[List[EntityObjectStorageSchema]] = list()
    upload_data: Optional[List[EntityObjectStorageSchema]] = list()


class FunctionEntryParameterSchema(BaseModel):
    package_dir: Optional[str] = None
    file_name: Optional[str] = None
    function_name: Optional[str] = None


class EnvironmentVariableParametersSchema(BaseModel):
    REDIS_HOST: str = settings.REDIS_HOST
    MONGO_HOST: str = settings.MONGODB_SERVER
    MINIO_URL: str = settings.MINIO_URL
    MINIO__ACCESS_KEY: str = settings.MINIO__ACCESS_KEY
    MINIO_SECRET_KEY: str = settings.MINIO_SECRET_KEY
    OUTPUTS_POINT: Optional[str] = None


class EventParamsSchema(BaseModel):
    lab_id: str
    task_id: str
    gateway_task_data: PhysicalTransmissionSchema
    datalab_launch: FunctionEntryParameterSchema
    memory_output: Optional[List] = list()
    user_id: str
    datalab_env: EnvironmentVariableParametersSchema = EnvironmentVariableParametersSchema()
    parameters: Optional[dict] = {}


class ParametersContext:

    def __init__(self):
        self.parameters = dict()
        self.transmission_map = dict()
        self.load_schemas = list()
        self.upload_schemas = list()

    def add(self, _rule: dict, key: str, frond_data: Any, transmission: bool, bucket_name: Optional[str] = None
            ):
        if transmission:
            # Data needs to be transferred inPodTo calculate in
            _parameter = EventParameter(type_string=_rule['type'], key=key, frond_data=frond_data).get_element()
            if isinstance(_parameter, tuple):
                _p, _schema = _parameter
                if isinstance(_schema, EntityObjectStorageSchema):
                    self.load_schemas.append(_schema.dict())
                else:
                    for _s in _schema:
                        self.load_schemas.append(_s.dict())
                self.parameters.update(_p)
            else:
                self.parameters.update(_parameter)
        else:
            _parameter = EventParameter(type_string=_rule['type'], key=key, frond_data=frond_data).get_element()
            _schema = EntityObjectStorageSchema(bucket=bucket_name,
                                                object_name=frond_data)
            self.upload_schemas.append(_schema.dict())
            self.parameters.update(_parameter)

    def get(self):
        return self.parameters, self.load_schemas, self.upload_schemas


class EventManager:
    _model = None
    parameter = None
    _id = None
    _parent_id = None
    event_params_entity = None

    def __init__(self, function_name: str, event_params: dict, user: UserModel):
        self._model = XmlToolSourceModel.objects(folder_name=function_name).first()
        self.parameter = self.meta(**event_params)
        self._tool_parameter()
        self._operator = user
        self.event_params_entity = self._parameter()

    @property
    def function_params(self) -> dict:
        if self.event_params_entity is None:
            try:
                self._parameter()
            except Exception as e:
                raise ValueError(f"The component event starts executing，Component parameter resolution exception： {e}")
        try:
            return self.event_params_entity.dict()
        except Exception as e:
            raise ValueError(f"The component event starts executing，Component parametersJsonSchemaSerialization exception： {e}")

    @property
    def asynchronous_uri(self) -> str:
        try:
            return ComponentInstance.objects(base_id=self._model.id).first().asynchronous_uri
        except MongoEngineException as e:
            print(datetime.utcnow(), e)
            raise ValueError("Component instance exception")

    def meta(self, **kwargs) -> dict:
        try:
            self._id = kwargs.pop("task_id")
        except KeyError:
            raise ValueError("The computation event unique identity is lost")
        try:
            self._parent_id = kwargs.pop('lab_id')
        except KeyError:
            raise ValueError("The computed event source is lost")
        return kwargs

    def _parameter(self) -> EventParamsSchema:
        _context = ParametersContext()
        _load = list()
        _upload = list()
        for k, v in self.parameter.items():
            _rule = self.inputs_rule.get(k)
            # Ifinputs with outputsConsistent variable names assume that naming an output requires capturing that output.
            _need_transmission = True if self.outputs_rule.get(k) is None else False
            _context.add(_rule, k, v, _need_transmission, self._parent_id)
        parameters, load_schemas, upload_schemas = _context.get()
        gateway_task_data = PhysicalTransmissionSchema(load_data=load_schemas, upload_data=upload_schemas)
        datalab_launch = FunctionEntryParameterSchema(package_dir="/home/app/function",
                                                      file_name=self._model.executable,
                                                      function_name=self._model.command)
        _event_parameter = EventParamsSchema(lab_id=self._parent_id,
                                             task_id=self._id,
                                             gateway_task_data=gateway_task_data,
                                             datalab_launch=datalab_launch,
                                             user_id=self._operator.id,
                                             parameters=parameters,
                                             memory_output=[]
                                             )
        return _event_parameter

    def _tool_parameter(self) -> None:
        _inputs = self._model.inputs
        _outputs = self._model.outputs
        self.inputs_rule = {i['name']: i for i in _inputs}
        self.outputs_rule = {i['name']: i for i in _outputs}
        required_parameter = [_['name'] for _ in _inputs if _["required"] is True]
        correlation_parameter = set([_['name'] for _ in _inputs]) & set([_['name'] for _ in _outputs])
        _difference_key = set(required_parameter).difference(set(self.parameter.keys()))
        if _difference_key:
            raise ValueError(f"Parameter exception：parameters{' | parameters'.join(_difference_key)}lost")

    async def trigger(self, conn: Optional[Redis] = None):
        try:
            _event = ToolTaskModel.objects(id=self._id).first()
            if _event is None:
                _event = AnalysisModel2.objects(id=self._parent_id).first()
            _task_queue_id = ComputeTaskManager.add_task(_event, self._operator.id)
            print(self.function_params)
            res = requests.post(self.asynchronous_uri,
                                json=self.function_params,
                                headers={"X-Callback-Url": f"http://{settings.SERVER_HOST}/api/components/callback/{_task_queue_id}"}
                                )
            keys = [self._id, f"{self._id}-task", f"{self._id}-resource"]
            await conn.delete(*keys)
            await conn.set(self._id + '-task', "Start")
            await conn.lpush(self._id, "==== DataLab Start Function ====")
            print(res.status_code, self.asynchronous_uri)
            if res.status_code != 202:
                raise ModuleNotFoundError(f"|{self._model.folder_name}| is not found")
            print({"msg": f"Component task {self._id} has been created", "data": {"id": self._id}})
        except Exception as e:
            return {"code": 400, "content": {"msg": f"Event identification{self._id}Failed to initiate computation： {e}"}}
        else:
            return {"code": 200, "content": {"msg": "", "data": {"id": self._id}}}

