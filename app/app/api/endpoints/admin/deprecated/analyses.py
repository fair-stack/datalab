"""
Deprecated:
Analysis based on analysis tools
"""

from typing import Union

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.models.mongo import (
    UserModel,
)
from app.usecases.deprecated import analyses_usecase

router = APIRouter()


@router.get("/",
            summary="List of analyses")
def read_analyses(
        name: Union[str, None] = None,
        creator: Union[str, None] = None,
        skeleton_id: Union[str, None] = None,
        state: Union[str, None] = None,
        page: int = 0,
        size: int = 10,
        sort: str = 'desc',
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param name:
    :param creator:
    :param skeleton_id:
    :param state:
    :param page:
    :param size:
    :param sort:
    :param current_user:
    :return:
    """
    content = analyses_usecase.read_analyses(
        name=name,
        creator=creator,
        skeleton_id=skeleton_id,
        state=state,
        page=page,
        size=size,
        viewer=current_user,
        only_own=False,      # You can see everyone else's
        sort=sort
    )

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))
