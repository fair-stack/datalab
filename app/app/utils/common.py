import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib
import pytz
from pydantic import BaseModel
from mongoengine import Document


def generate_uuid(length=26) -> str:
    """
    uuid.uuid4().replace("-", '') ->  UUID('9512ed96-ef2e-4108-9117-c7dafc334a11') -> 2973d296db174f89bb75473c85a0d12e
    :return: str
    """
    uid = str(uuid.uuid4()).replace("-", "")
    if length > 0:
        return uid[0:length]
    else:
        return uid


def convert_mongo_document_to_data(document: Document,
                                   norm_id: bool = True,
                                   datetime_to_local_tz: Optional[int] = 8,
                                   to_datetime_format: str = "%Y-%m-%d %H:%M:%S") -> Dict:
    """
    mongoengine.document._data Unable to convert involved EmbeddedDocument The situation of，
    Notice that in the results `_id` correspondence Model Inside of `id`， and ReferenceField the `user` Convert directly to str

    :param document:
    :param norm_id: Whether the _id Convert to id
    :param datetime_to_local_tz:  Whether the
    :param to_datetime_format:
    :return:
    """
    _data = document.to_mongo().to_dict()
    if norm_id is True:
        _data["id"] = _data.get("_id")
        _data.pop("_id", None)
    if isinstance(datetime_to_local_tz, int):
        for k, v in _data.items():
            if isinstance(v, datetime):
                _data[k] = (v + timedelta(hours=datetime_to_local_tz))
                if to_datetime_format:
                    _data[k] = _data[k].strftime(f'{to_datetime_format}')
    return _data


def convert_mongo_document_to_schema(document: Document,
                                     schema_cls: BaseModel,
                                     user: bool = False,
                                     revers_map: list = None,
                                     revers_id: bool = False,
                                     serialization: list = None
                                     ) -> Dict:
    """
    Don't bother to make two transitions One time fromDocument Convert into BaserModel
    :param document: Mongo ORM Object
    :param schema_cls: willDocumentConvert tothe BaseModel
    :param user: willDocumenttheConvert tothe
    :param revers_map: willDocumenttheConvert tothe
    :param serialization: Foreign keys are fully serialized
    :return:
    """
    _data = document.to_mongo().to_dict()
    _data["id"] = str(_data.pop("_id"))
    if user:
        _data['user'] = document.user.name
    if revers_map:
        for k in revers_map:
            try:
                if revers_id:
                    _data[k] = document.__getattribute__(k).id
                else:
                    _data[k] = document.__getattribute__(k).name
            except Exception as e:
                pass

    # elif user and revers_map is None:
    #     _data['user'] = document.user.name
    schema_instance = schema_cls(**{k: v.strftime('%Y/%m/%d %H:%M:%S') if isinstance(v, datetime) else v for k, v
                                    in _data.items()})
    return schema_instance.dict()
    # return {k: v.strftime('%Y/%m/%d %H:%M:%S') if isinstance(v, datetime) else v for
    #         k, v in schema_instance.dict().items()}


def get_md5(s):
    m = hashlib.md5()
    m.update(s.encode())
    return m.hexdigest()
