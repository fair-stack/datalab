# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:crud_da
@time:2023/06/15
"""
import re
from datetime import datetime
from app.models.mongo import (
    DataFileSystem,
    UserModel,

)
from app.utils.common import generate_uuid
from app.models.mongo.public_data import PublicDataFileModel
from app.models.mongo.digital_asset import ExperimentsDigitalAssetsModel
from app.service.response import DataLabResponse
from . import MAXIMUM_RETURN_LENGTH
from enum import Enum
from typing import Optional, List, Dict
from app.schemas.dataset import DatasetV2Schema
from app.utils.common import convert_mongo_document_to_schema


class FromSource(Enum):
    mydata = "mydata"
    share = "share"
    public = "public"
    findata = "findata"


class OrderByEnum(Enum):
    create_time: int = 1
    data_type: int = 2
    name: int = 3
    size: int = 4


ORDER_BY_FILED = {
    1: "-updated_at",  # Time reversal
    2: "updated_at",  # Time alignment
    3: "-file_extension",  # Type inversion
    4: "file_extension",  # Type positive row
    5: "-name",  # Name alignment
    6: "name",  # Name alignment
    7: "-size",  # Size positive row
    8: "size"  # Size positive row
                  }


def get_model(pk: str, user: UserModel):
    _model = DataFileSystem.objects(id=pk, user=user, deleted=False).first()
    return _model


def delete(pk: str, user: UserModel):
    _model = get_model(pk, user)
    if _model is None:
        return DataLabResponse.failed("File does not exist")
    sons = get_sons(_model)
    if sons:
        # DataFileSystem.objects(id__in=sons).update(deleted=True)
        DataFileSystem.objects(id__in=sons).delete()
    return DataLabResponse.successful()


def get_sons(model: DataFileSystem, sons: list = []):
    sons.append(model.id)
    if model.is_dir:
        son = DataFileSystem.objects(parent=model.id)
        for i in son:
            sons.append(i.id)
            get_sons(i, sons)
    return sons


def update(pk: str, user: UserModel, **kwargs):
    name = kwargs.get("name")
    _double_quotation = '"'
    _single_quotation = "'"
    character = re.findall(f'[/${_double_quotation}{_single_quotation}*<>?\\/|：:]', name)
    if character:
        return DataLabResponse.failed(f"An invalid character exists in the name< {' '.join(character)} >")
    if name[0] == " " or name[0] == ".":
        return DataLabResponse.failed("No Spaces or.As a head start")
    _model = get_model(pk, user)
    if _model is None:
        return DataLabResponse.failed("Data does not exist")
    _model.name = name
    _model.updated_at = datetime.utcnow()
    try:
        _model.save()
    except Exception as e:
        print(e)
        return DataLabResponse.failed("Change failed")
    else:
        return DataLabResponse.successful()


def search(user: UserModel, name: Optional[str] = None,  skip: int = 0, limit: int = 10, order_by: int = 1):
    if limit > MAXIMUM_RETURN_LENGTH:
        return DataLabResponse.failed()
    params = dict()
    key, value = ("name__contains", name) if name is not None else ("parent", "root")
    params[key] = value
    _models = DataFileSystem.objects(user=user, deleted=False, **params).order_by(ORDER_BY_FILED.get(order_by))
    total = _models.count()
    _models = _models.skip(skip).limit(limit)
    skip = skip*limit
    _models = _models[skip: skip + limit]
    _data = list(map(lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema,
                                                                user=True, revers_map=['user']),
                     _models))
    return DataLabResponse.successful(data=_data, total=total)


def next_depth(order_by: int, pk: str, user: UserModel, skip: int = 0, limit: int = 10):
    if limit > MAXIMUM_RETURN_LENGTH:
        return DataLabResponse.failed()
    _models = DataFileSystem.objects(parent=pk, user=user, deleted=False).order_by(ORDER_BY_FILED.get(order_by))
    total = _models.count()
    _models = _models.skip(skip).limit(limit)
    _data = list(map(lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema,
                                                                user=True, revers_map=['user']),
                     _models))
    return DataLabResponse.successful(total=total, data=_data)


def add_digital(data: List[Dict], experiment_id: str, user: UserModel):
    _models = list()
    error_list = list()
    for i in data:
        if i["type"] == "mydata" or i['type'] == "share":

            _data_model = DataFileSystem.objects(id=i["id"], user=user.id, deleted=False).first()
            if _data_model is None:
                error_list.append(i["id"])
                continue
            if ExperimentsDigitalAssetsModel.objects(from_source=_data_model, project=experiment_id).first() is None:
                _digital_id = generate_uuid()
                _model = ExperimentsDigitalAssetsModel(
                    id=_digital_id,
                    name=_data_model.name,
                    is_file=_data_model.is_file,
                    data_size=_data_model.data_size,
                    data_path=_data_model.data_path,
                    user=user,
                    description=_data_model.description,
                    from_source=_data_model,
                    file_extension=_data_model.file_extension,
                    parent=_data_model.parent,
                    project=experiment_id)
                _models.append(_model)
        elif i["type"] == "public":
            _data_model = PublicDataFileModel.objects(id=i["id"], deleted=False).first()
            if _data_model is None:
                error_list.append(i["id"])
            if ExperimentsDigitalAssetsModel.objects(from_source=_data_model,
                                                         project=experiment_id).first() is None:
                _digital_id = generate_uuid()
                _model = ExperimentsDigitalAssetsModel(
                    id=_digital_id,
                    name=_data_model.name,
                    is_file=_data_model.is_file,
                    data_size=_data_model.data_size,
                    data_path=_data_model.data_path,
                    user=user,
                    description=_data_model.description,
                    from_source=_data_model,
                    file_extension=_data_model.file_extension,
                    parent=_data_model.parent,
                    project=experiment_id)
                _models.append(_model)
        elif i["type"] == "findata":
            pass

    try:
        for i in _models:
            try:
                i.save()
            except Exception as e:
                print(e)
    except Exception as e:
        print(e)
        return DataLabResponse.failed("Failure to add experimental data")
    else:
        if error_list:
            return DataLabResponse.failed(f"ID {','.join(error_list)},Add failure")
        return DataLabResponse.successful()
