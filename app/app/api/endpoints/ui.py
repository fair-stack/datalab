from fastapi import APIRouter, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.usecases import ui_usecase

router = APIRouter()


@router.get("/platform",
            summary="Platform Configuration Details")
def read_platform():
    data = ui_usecase.read_platform()
    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no platform found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.get("/indexui",
            summary="Home Configuration Details")
def read_indexui():
    data = ui_usecase.read_indexui()

    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no indexui found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.get("/experimentui",
            summary="Experiment page configuration details")
def read_experimentui():
    data = ui_usecase.read_experimentui()

    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no experimentui found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.get("/skeletonui",
            summary="Profiling tool page configuration details")
def read_skeletonui():
    data = ui_usecase.read_skeletonui()

    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no skeletonui found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})
