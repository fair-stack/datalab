# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:datasets
@time:2023/05/09
"""
import datetime
from minio.deleteobjects import DeleteObject
from fastapi import status
from fastapi.responses import JSONResponse
from app.utils.middleware_util import get_s3_client
from app.models.mongo.public_data import \
    PublicDatasetModel,\
    PublicDataFileModel,\
    PublicDatasetOptionModel
from app.schemas.dataset import DatasetsListResponseSchema
from typing import List, Dict, AnyStr


class DatasetsManager:

    INJECT_SOURCES_ALLOW = {"InstDb", "DataSpace", "FairMan"}

    @staticmethod
    def datasets(admin: bool = False) -> List[Dict]:
        _data = list()
        for i in PublicDatasetModel.objects(links__ne="LOCAL"):
            if admin is False:
                if i.access == "PUBLIC":
                    files_num = PublicDataFileModel.objects(datasets=i.id).count()
                    _data.append(DatasetsListResponseSchema(id=i.id, name=i.name, source=i.data_type,
                                                            description=i.description, files_total=files_num).dict())
            else:
                files_num = PublicDataFileModel.objects(datasets=i.id).count()
                _data.append(DatasetsListResponseSchema(id=i.id, name=i.name, source=i.data_type,
                                                        description=i.description, files_total=files_num).dict())
        for i in PublicDataFileModel.objects(file_extension="datasets"):
            if admin is False:
                if i.access == "PUBLIC":
                    files_num = PublicDataFileModel.objects(datasets=i.id).count()
                    _data.append(DatasetsListResponseSchema(id=i.id, name=i.name, source="LOCAL",
                                                            description=i.description, files_total=files_num).dict())
            else:
                files_num = PublicDataFileModel.objects(datasets=i.id).count()
                _data.append(DatasetsListResponseSchema(id=i.id, name=i.name, source="LOCAL",
                                                        description=i.description, files_total=files_num).dict())
        return _data

    @staticmethod
    def access() -> bool:
        options = PublicDatasetOptionModel.objects.first()
        return options.access

    def inject(self, source_refer: str) -> bool:
        if source_refer not in self.INJECT_SOURCES_ALLOW:
            return False
        return True

    def datasets_inject(self, datasets_id: str) -> AnyStr:
        _datasets_model = PublicDatasetModel.objects(id=datasets_id).first()
        if _datasets_model:
            # TODO The dataset already exists，Update
            _start_time_at = datetime.datetime.utcnow()
        return datasets_id

    @staticmethod
    def remove(datasets_id):
        _datasets_model = PublicDatasetModel.objects(id=datasets_id).first()
        if _datasets_model is None:
            return "Deletion failure，The dataset does not exist"
        _datasets_files_model = PublicDataFileModel.objects(datasets=datasets_id)
        oss_client = get_s3_clients()
        for _file in _datasets_files_model:
            object_delete_list = [DeleteObject(_.object_name) for _ in
                                  oss_client.list_objects(_datasets_model.id, recursive=True)]
            for _ in object_delete_list:
                pass
