# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:standalone_deploy
@time:2023/07/06
"""
from fastapi import (
    APIRouter,
    Depends,
    status,
    BackgroundTasks
)
from fastapi.responses import JSONResponse
from app.api import deps
from app.core.config import settings
from app.core.gate import PublishTask
from app.models.mongo import UserModel
from app.standalone.components.builder import StandaloneFunctionDeployer

router = APIRouter()


@router.post("/standalone/deploy/{component_id}")
def deploy_function(component_id: str,
                    background_task: BackgroundTasks,
                    current_user: UserModel = Depends(deps.get_current_user)):
    StandaloneFunctionDeployer(component_id, current_user.id).create_temporary()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "Success", "id": component_id})


if __name__ == '__main__':
    ...
