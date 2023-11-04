from typing import Union, Optional

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.models.mongo import UserModel
from app.usecases import tools_usecase

router = APIRouter()


@router.get("/",
            summary="Component list")
def read_tools(
        state: Optional[Union[bool, str]] = '',
        current_user: UserModel = Depends(deps.get_current_user)):

    data = tools_usecase.read_tools_in_tree_format(state=state, audit="Approved by review")
    content = {
        'msg': "success",
        'data': data
    }
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/{tool_id}",
            summary="Component Details")
def read_tool(tool_id: str,
              current_user: UserModel = Depends(deps.get_current_user)):
    data = tools_usecase.read_tool(tool_id)
    content = {"msg": "success", "data": data}
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))
