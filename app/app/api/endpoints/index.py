from typing import Union, Optional

from fastapi import APIRouter, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTasks

from app.usecases import skeletons_usecase2

"""
No login required，Accessible functional interfaces
"""


router = APIRouter()


@router.get("/skeletons/",
            summary="List of analysis tools")
async def read_skeletons(
        background_tasks: BackgroundTasks,
        name: Union[str, None] = None,
        category: Union[str, None] = None,
        page: int = 0,
        size: int = 10
):
    """
    List of analysis tools（Front desk）

    :param background_tasks:
    :param name:
    :param category:
    :param page:
    :param size:
    :return:
    """
    # t1 = time.time()
    code, msg, content = await skeletons_usecase2.read_skeletons(
        menu=skeletons_usecase2.MENU_SKELETON,
        background_tasks=background_tasks,
        name=name,
        category=category,
        page=page,
        size=size
    )
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    # t2 = time.time()
    # print(f'read_skeletons: {t2 - t1}')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/skeletons/detail",
            summary="Analysis Tool Details")
async def read_skeleton(
        skeleton_id: str,
        user_id: Union[str, None] = None,
):
    """

    :param skeleton_id:
    :param user_id:
    :return:
    """
    code, msg, data = await skeletons_usecase2.read_skeleton(skeleton_id=skeleton_id, viewer_id=user_id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.get("/skeletons/aggs",
            summary="Analysis tool category statistics")
async def read_skeletons_aggs(
        name: Optional[str] = None
):
    """
    List of analysis tools（Front desk）

    :return:
    """
    # t1 = time.time()
    data = await skeletons_usecase2.read_skeletons_aggregates_by_category(
        is_online=True,
        name=name
    )
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))
