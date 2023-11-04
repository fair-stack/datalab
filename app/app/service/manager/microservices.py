# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:microservices
@time:2023/05/18
"""
import requests
from typing import Optional
from datetime import datetime
from app.models.mongo import (
    UserModel,
    MicroservicesModel,
    MicroservicesServerStateEnum,
)
from app.core.note.gateway import ApiSix
from app.core.config import settings


class MicroservicesManager:
    @staticmethod
    def is_integration(model: MicroservicesModel):
        router_integration = MicroservicesModel.objects(router=model.router).first()
        if router_integration is not None:
            return True, "The path has been registered，URLIt has uniqueness and cannot be repeated"
        name_is_integration = MicroservicesModel.objects(name=model.name).first()
        if name_is_integration is not None:
            return True, "Duplicate service name"
        uri_integration = MicroservicesModel.objects(host=model.host, port=model.port).first()
        if uri_integration is not None:
            return True, f"The service source is registered，Service registration name in the platform<{uri_integration.name}>"
        return False, "Not registered"

    @staticmethod
    def integration(model: MicroservicesModel):
        _gateway = ApiSix()
        _upstream_id = _gateway.register_upstream(name=model.name,
                                                  host=f"{model.host}:{model.port}")
        _uris = list()
        _uris.append(f"{settings.SERVER_HOST}/dupyter/{model.router}")
        # ParsingopenapiUnder theURIInformation generationRouter
        # if model.file is not None:
            #
        _gateway.register_router(model.name, model.router, _upstream_id)

    @staticmethod
    def is_healthy(model: MicroservicesModel):
        _url = f"{model.host}:{model.port}"
        resp = requests.get(_url)
        try:
            _resp_code = resp.status_code
            return True if _resp_code > 99 | _resp_code < 400 else False, "No abnormal service status"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def offline(model: MicroservicesModel):
        model.deleted = True
        model.modify_at = datetime.utcnow()
        model.save()
        #  API-SIX GatewayreleaseUpstreamwithRouter
