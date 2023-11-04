# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:microservices
@time:2023/06/27
"""
from fastapi import (
    APIRouter,

)
from app.results.response import DataLabResponse
from app.models.mongo import (
    UserModel,
    MicroservicesModel,
    MicroservicesServerStateEnum,
)
from app.schemas.microservices import MicroservicesSchemas
from app.utils.common import convert_mongo_document_to_schema, generate_uuid
router = APIRouter()


@router.get("/services", summary="List of portal microservices")
async def get_microservices():
    try:
        _models = MicroservicesModel.objects(deleted=False, state="AVAILABLE").order_by("-modify_at")
        _total_size = _models.count()
        _data = [{"name": i.name, "router": i.router, "id": i.id} for i in _models]
    except Exception as e:
        print(e)
        return DataLabResponse.error("Request handling exception")
    else:
        return DataLabResponse.successful(total_size=_total_size, data=_data)


if __name__ == '__main__':
    ...
