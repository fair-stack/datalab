# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:microservices
@time:2023/05/25
"""
from fastapi import (
    APIRouter,
    Depends,
    Form,
    File,
    UploadFile,
)
from typing import Optional
from datetime import datetime
from app.api import deps
from app.results.response import DataLabResponse
from app.models.mongo import (
    UserModel,
    MicroservicesModel,
    MicroservicesServerStateEnum,
)
from app.schemas.microservices import MicroservicesSchemas
from app.utils.common import convert_mongo_document_to_schema, generate_uuid
from app.service.manager.microservices import MicroservicesManager
router = APIRouter()


@router.get("/services", summary="List of registered microservices")
async def get_microservices(page: Optional[int] = 0,
                            size: Optional[int] = 10,
                            name: Optional[str] = None,
                            user: Optional[str] = None,
                            state: Optional[str] = None,
                            current_user: UserModel = Depends(deps.get_current_user)):
    if size > 100:
        return DataLabResponse.failed("Request paging parameter is too large，Malicious request")
    try:
        query_set = dict()
        if name and name != "":
            query_set["name__icontains"] = name
        if user and user != "":
            users = UserModel.objects(name__icontains=user)
            query_set["user__in"] = users
        if state and state != "":
            query_set["state"] = state
        skip = page * size
        _models = MicroservicesModel.objects(deleted=False, **query_set).order_by("-modify_at")
        _total_size = _models.count()
        data = _models.skip(skip).limit(size)
        _data = list(map(lambda x: convert_mongo_document_to_schema(x, MicroservicesSchemas, user=True), data))
    except Exception as e:
        print(e)
        return DataLabResponse.error("Request handling exception")
    else:
        return DataLabResponse.successful(total_size=_total_size, data=_data)


@router.post("/integration/server", summary="Service integration")
async def integration_server(
        name: str = Form(...),
        host: str = Form(...),
        port: int = Form(...),
        description: Optional[str] = Form(None),
        router_path: str = Form(...),
        file: UploadFile = File(None),
        current_user: UserModel = Depends(deps.get_current_user)
):
    upstream_id = generate_uuid()
    router_id = generate_uuid()
    # router_path = f'/{router_id}'
    _model = MicroservicesModel(
        id=generate_uuid(),
        name=name,
        host=host,
        port=port,
        description=description,
        upstream_id=upstream_id,
        router_id=router_id,
        user=current_user,
        modify_user=current_user,
        router=router_path,
        state=MicroservicesServerStateEnum.available
    )

    # Check for duplicate service items
    _flag, _msg = MicroservicesManager.is_integration(_model)
    if _flag is True:
        return DataLabResponse.failed(_msg)
    MicroservicesManager.integration(_model)
    #  Test that communication is working
    # _healthy_flag, _healthy_msg = MicroservicesManager.is_healthy(_model)
    # if _healthy_flag is False:
    #     return DataLabResponse.failed(_healthy_msg)
    try:
        _model.save()
    except Exception as e:
        print(e)
        return DataLabResponse.error("Service to be integrated is abnormal")
    else:
        # If it existsOpenAPIthe .json .yamlFiles are dumped and re-registered for the serviceURIRegister.
        # if file is not None:
        #     with open(file.filename, 'wb') as f:
        #         f.write(await file.read())
        # the Static methods .integration
        # MicroservicesManager.integration(_model)
        return DataLabResponse.successful()


@router.post("/integration/software", summary="Service integration")
async def integration_software_service(
        current_user: UserModel = Depends(deps.get_current_user)
):
    return DataLabResponse.error("Not open for now")


@router.delete("/offline/{service_id}", summary="the")
async def delete_cluster_microservices(
        service_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
                                       ):
    _model = MicroservicesModel.objects(id=service_id).first()
    if _model is None:
        return DataLabResponse.failed("Service does not exist")
    try:
        _model.modify_user = current_user
        MicroservicesManager.offline(_model)
    except Exception as e:
        print(e)
        return DataLabResponse.error("The service failed to log off")
    else:
        return DataLabResponse.successful()


@router.put('/update/service/{service_id}', summary="Modify the service metadata")
async def update_service_metadata(
        service_id: str,
        name: str = Form(None),
        current_user: UserModel = Depends(deps.get_current_user)

):
    try:
        _model = MicroservicesModel.objects(id=service_id).first()
        if _model is None:
            return DataLabResponse.failed("Service does not exist")
        if name:
            _model.name = name
            _model.modify_at = datetime.utcnow()
            _model.modify_user = current_user
            _model.save()
    except Exception as e:
        print(e)
        return DataLabResponse.error("Service metadata modification failed")
    else:
        return DataLabResponse.successful()
