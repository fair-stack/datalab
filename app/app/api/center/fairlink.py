import time
from functools import reduce
from mongoengine.errors import DoesNotExist
from app.utils.middleware_util import get_s3_client
from app.models.mongo.dataset import DataFileSystem
from fastapi import (
    APIRouter,
    Depends,
    status,
Request
)

from fastapi.responses import JSONResponse
from app.schemas.tools_tree import ToolsTreeSchema, ToolsTreeResponseSchema
from app.schemas.tool_source import ToolSourceBaseSchema
from app.models.mongo import UserModel, ExperimentModel, ToolTaskModel, ToolsTreeModel, XmlToolSourceModel, \
    StorageResourceAllocatedModel
from app.api import deps
from app.models.mongo.dataset import DataFileSystem
from app.utils.common import convert_mongo_document_to_schema, convert_mongo_document_to_data
from app.utils.resource_util import get_cache_cumulative_num
from app.schemas.dataset import DatasetV2Schema
from app.fair_stack.instdb import InstDBFair
from app.models.mongo.fair import InstDbModel, InstDbAuthorModel
router = APIRouter()

@router.post('/instdb')
async def instdb_link(
        url: str,
        secret_key: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    inst_cls = InstDBFair.create_link(url, secret_key)
    if inst_cls is not None:
        _datasets = inst_cls.datasets_meta_data()
        if _datasets:
            for _ in _datasets:
                authors = list()
                for _author in _.pop('author'):
                    authors.append(InstDbAuthorModel(**_author))
                _['author'] = authors
                # InstDbModel(**_).save()
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"data": inst_cls.datasets_meta_data(),
                                     "msg": "Successful"})
    else:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "Successful"})
