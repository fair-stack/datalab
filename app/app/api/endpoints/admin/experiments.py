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
from app.usecases import experiments_usecase

router = APIRouter()


@router.get("/",
            summary="List of experiments (Trial run experiments are not included)")
def read_experiments(
        is_shared: Union[bool, None] = None,
        name: Union[str, None] = None,
        creator: Union[str, None] = None,
        page: int = 0,
        size: int = 10,
        sort: str = 'desc',
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    NOTE： Experiments during the trial run are not shown (is_trial=True)

    :param is_shared:
    :param name:
    :param creator:
    :param page:
    :param size:
    :param sort:
    :param current_user:
    :return:
    """
    content = experiments_usecase.read_experiments(
        is_shared=is_shared,
        name=name,
        creator=creator,
        page=page,
        size=size,
        viewer=current_user,
        only_own=False,     # You can see everyone else's
        sort=sort
    )

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))
