# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:results
@time:2022/10/31
"""

from app.utils.k8s_util.nodes import K8SNode
from fastapi import (
    APIRouter,
    Depends,
    status,
)
from app.models.mongo import (
    ExperimentModel,
    SkeletonModel2,
)
import os
from fastapi.responses import JSONResponse
from app.models.mongo.public_data import PublicDatasetModel
router = APIRouter()


@router.get('/')
def get_lab_report():
    try:
        physical_resources = K8SNode().get_nodes_details()
        physical_resources['experiment_total'] = ExperimentModel.objects(is_trial=False).count()
        physical_resources['tools__total'] = SkeletonModel2.objects(state='APPROVED', is_online=True).count()
        physical_resources['public_data_total'] = PublicDatasetModel.objects.count()
        physical_resources['version'] = "1.1.1"
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Success",
                                     "data": physical_resources})
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": str(e),
                                     "data": None})


@router.get('/restart/storage', summary="DEV-Restart storage with")
async def restart_oss():
    try:
        os.system("docker restart minio3")
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": str(e)})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})
