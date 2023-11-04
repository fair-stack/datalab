# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:visualization
@time:2023/03/21
"""
import sys
sys.path.append('/Users/wuzhaochen/Desktop/workspace/datalab/app')
import json
import pandas as pd
from typing import Any
from app.schemas.visualization import VisualizationDataInCrate, VisualizationComponentsResponse
from app.models.mongo import VisualizationComponentModel, DataFileSystem, UserModel
from app.models.mongo.fair import FairMarketComponentsModel
from app.utils.middleware_util import get_s3_client
from app.models.mongo.public_data import PublicDataFileModel
fileUrl = "fileUrl"
background = "background"
FAIR_MARKET_VISUALIZATION_TYPE_STATIC_FILE = "fileUrl"
FAIR_MARKET_VISUALIZATION_TYPE_FILE_STREAM = "fileUrl"
FAIR_MARKET_VISUALIZATION_TYPE_FILE_READER = "FileToString"
FAIR_MARKET_VISUALIZATION_TYPE_FILE_READER2 = "content"
FAIR_MARKET_VISUALIZATION_TYPE_CSV_TABLE = "CsvTable"


class VisualizationManager:

    def __init__(self, data: VisualizationDataInCrate = None, revers_functions: dict = None):
        self.data = data
        self.data.component_id = self.data.component_id.split('/')[-2]
        self.data_model = None
        self.functions_map = revers_functions
        if revers_functions is not None:
            for k, v in revers_functions.items():
                visualization_backend_function_class, visualization_backend_function = v.split('.')
                if visualization_backend_function_class == self.__class__.__name__:
                    self.functions_map[k] = self.__getattribute__(visualization_backend_function)
        self.object_storage_bucket = None
        self.object_storage_name = None

    @property
    def file_path(self) -> str:
        if self.data is not None:
            _data = DataFileSystem.objects(id=self.data.data_id).first()
            if _data is None:
                return ""
        return ""

    def check_file_exists(self):
        try:
            if self.data_model is None:
                self.data_model = DataFileSystem.objects(id=self.data.data_id).first()
            if self.data_model.from_source is not None and self.data_model.from_source != '':
                source_data = self.data_model
            else:
                source_data = DataFileSystem.objects(id=self.data_model.from_source).first()
            if source_data.data_type == "myData":
                self.object_storage_bucket = source_data.user.id
                self.object_storage_name = source_data.data_path
                client = get_s3_client()
                from minio import Minio
                if not client.bucket_exists(self.object_storage_bucket):
                    client.make_bucket(self.object_storage_bucket)
                try:
                    client.stat_object(self.object_storage_bucket, self.object_storage_name)
                except Exception:
                    client.fput_object(self.object_storage_bucket, self.object_storage_name, self.object_storage_name)
            else:
                self.object_storage_bucket = source_data.lab_id
                self.object_storage_name = f"{source_data.task_id}/{source_data.data_path}"
            if source_data is None:
                self.object_storage_bucket = PublicDataFileModel.objects(id=self.data.data_id).first().datasets.id
                self.object_storage_name = PublicDataFileModel.objects(id=self.data.data_id).first().data_path
        except Exception as e:
            print(e)

    def native_csv_table(self):
        client = get_s3_client()
        _data = pd.read_csv(client.get_object(self.object_storage_bucket, self.object_storage_name)).to_dict('records')
        return _data

    def native_static(self):
        client = get_s3_client()
        _name = f'/home/datalab/dist/market_component/static/{self.data_model.id}.{self.data_model.name.rsplit(".")[-1]}'
        with open(_name, 'wb') as f:
            f.write(client.get_object(self.object_storage_bucket, self.object_storage_name ).read())
        return _name.replace('/home/datalab/dist', "")

    def native_txt_read(self):
        client = get_s3_client()
        _data = client.get_object(self.object_storage_bucket, self.object_storage_name).read().decode()
        return _data

    @staticmethod
    def map(data_id: str):
        print(data_id)
        _d = DataFileSystem.objects(id=data_id).first()
        if _d is None:
            return VisualizationComponentsResponse()
        suffix = _d.name.rsplit(".")[-1]
        if len(suffix) < 1:
            return VisualizationComponentsResponse()
        _front_component = VisualizationComponentModel.objects(support__iexact=suffix,
                                                               enable=True).order_by("-update_at")
        _first_component = _front_component.first()
        others = list()
        if _first_component is not None:
            # Determine if the available components are ready to install
            # source__installed = True
            _installed = None
            _static_id = None
            _static_path = None
            for _index, i in enumerate(_front_component):
                if _index == 0:
                    _static_path = f"/market_component/{_front_component.first().source.id}/dist"
                    _installed = i.source.installed
                    _static_id = i.source.id
                else:
                    others.append({"path": f"/market_component/{i.source.id}/dist",
                                   "installed": i.source.installed,
                                   "name": i.name,
                                   "id": i.source.id})
            _response_data = VisualizationComponentsResponse(data=_static_path,
                                                             name=_front_component.first().name,
                                                             installed=_installed,
                                                             others=others,
                                                             id=_static_id)
        else:
            _response_data = VisualizationComponentsResponse(data=None)
        return _response_data

    def create_data(self, user: UserModel):
        if self.data is not None:
            visualization_model = VisualizationComponentModel.objects(
                source=FairMarketComponentsModel.objects(id=self.data.component_id).first()).first()
            if visualization_model is None:
                return {}
            response_data = self.analysis_schema(visualization_model.response_schema)
            visualization_model.update(used_counts=visualization_model.used_counts+1)
            return response_data

    def analysis_schema(self, schema_list: list):
        if schema_list:
            for i in schema_list:
                if i.get('key') == "data":
                    source_code = i
            # source_code = schema_list[0]
            # print(schema_list)
            return self.traverse_list_dict(source_code, self.revers_market_component_schema)

    def revers_file(self):
        self.check_file_exists()

    @property
    def files_type(self):
        return [FAIR_MARKET_VISUALIZATION_TYPE_FILE_READER, FAIR_MARKET_VISUALIZATION_TYPE_FILE_READER2,
                FAIR_MARKET_VISUALIZATION_TYPE_CSV_TABLE,
                FAIR_MARKET_VISUALIZATION_TYPE_STATIC_FILE, FAIR_MARKET_VISUALIZATION_TYPE_FILE_STREAM]

    def revers_market_component_schema(self, x):
        _schema_data = None
        if x in self.files_type:
            self.revers_file()
        if self.functions_map.get(x) is not None:
            _schema_data = self.functions_map.get(x)()
        return _schema_data

    def traverse_list_dict(self, data, revers_function):
        try:
            data = eval(data)
        except TypeError:
            pass
        new_data = dict()
        for key, value in data.items():
            _ls = eval(value)
            try:
                _ = _ls["fileUrl"]
                key = 'fileUrl'
            except KeyError:
                pass
            print("revers_", key, _ls)
            _d = revers_function(key)
            if isinstance(value, list):
                value.append(_d)
            else:
                value = _d
            new_data[key] = [value]
        if new_data.get("key") != "data":
            new_data["key"] = "data"
        # if isinstance(data, list):
        #     for i, x in enumerate(data):
        #         data[i] = self.traverse_list_dict(x, revers_function)
        # elif isinstance(data, dict):
        #     for key, value in data.items():
        #         print(key, value)
        #         data[key] = self.traverse_list_dict(value, revers_function)
        # else:
        #     print(data)
        #     data = revers_function(data)
        return new_data

    @classmethod
    def create_from_requests(cls, data: VisualizationDataInCrate):
        functions = {
            FAIR_MARKET_VISUALIZATION_TYPE_STATIC_FILE: f"{cls.__name__}.native_static",
            FAIR_MARKET_VISUALIZATION_TYPE_FILE_STREAM: f"{cls.__name__}.native_static",
            FAIR_MARKET_VISUALIZATION_TYPE_FILE_READER: f"{cls.__name__}.native_txt_read",
            FAIR_MARKET_VISUALIZATION_TYPE_FILE_READER2: f"{cls.__name__}.native_txt_read",
            FAIR_MARKET_VISUALIZATION_TYPE_CSV_TABLE:  f"{cls.__name__}.native_csv_table"
        }
        return cls(data, functions)


class VisualizationManager2:

    @staticmethod
    def create_response(params: VisualizationDataInCrate = None):
        # data = DataFileSystem.objects(id=params['data_id']).first()
        object_id = params["component_id"].split('/')[2]
        # visualization_model = VisualizationComponentModel.objects(
        #     source=FairMarketComponentsModel.objects(id=object_id).first()).first()
        # response_schema = visualization_model.response_schema
        response_schema = [
            {"key": "suffix", "value": "jpg,png,bmp,gif,jpeg,raw"},
            {"key": "data", "value": "{fileUrl:[],background:\"#fff\"}"},
            {"key": "type", "value": "fileUrl"}]
        response_schema = {i['key']: i["value"] for i in response_schema}
        print(response_schema)


    @staticmethod
    def schema_map(schema: Any, data: DataFileSystem):
        pass



if __name__ == '__main__':
    VisualizationManager2.create_response({
  "data_id": "03a945873b4b4115bf5f3d27ce",
  "component_id": "/market_component/6437bc02da4c14bb176ce0c7/dist"
})
