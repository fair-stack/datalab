from datetime import datetime
from typing import Optional, Dict

from fastapi import APIRouter, Depends, status, UploadFile, Form
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.forms import (
    UiUpdateForm,
)
from app.models.mongo import (
    ExperimentUiModel,
    IndexUiModel,
    PlatformModel,
    SkeletonUiModel,
    UserModel,
)
from app.usecases import ui_usecase
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.file_util import convert_uploaded_img_to_b64_stream_str, chunked_copy

router = APIRouter()


@router.post("/platform",
             summary="Platform Configuration Creation")
def create_platform(
        file: UploadFile,
        name: str = Form(),
        copyright: str = Form(default=None),
        filingNo: str = Form(default=None),
        current_user: UserModel = Depends(deps.get_current_user)):
    total = PlatformModel.objects.count()
    if total > 0:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={"msg": "platform already exists, only one is allowed"})

    # name Judgment
    name = name.strip()
    if name == '':
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid name: {name}"})

    # copyright Judgment
    if copyright is not None:
        copyright = copyright.strip()
        if copyright == '':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid copyright: {copyright}"})

    # filingNo Judgment
    if filingNo is not None:
        filingNo = filingNo.strip()
        if filingNo == '':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid filingNo: {filingNo}"})

    logo = convert_uploaded_img_to_b64_stream_str(file.file)

    platform = PlatformModel(
        id=generate_uuid(length=26),
        name=name,
        copyright=copyright,
        filingNo=filingNo,
        logo=logo
    )
    platform.save()

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success"})


@router.get("/platform",
            summary="Platform Configuration Details")
def read_platform(
        current_user: UserModel = Depends(deps.get_current_user)):
    data = ui_usecase.read_platform()
    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no platform found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.put("/platform",
            summary="Platform configuration modification")
def update_platform(
        file: Optional[UploadFile] = None,
        name: Optional[str] = Form(default=None),
        copyright: Optional[str] = Form(default=None),
        filingNo: Optional[str] = Form(default=None),
        current_user: UserModel = Depends(deps.get_current_user)):
    platform = PlatformModel.objects.first()
    if platform is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "platform not found"})

    # name Judgment
    if name:
        name = name.strip()
        if name == '':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid name: {name}"})
    # logo Upload
    if file:
        logo = convert_uploaded_img_to_b64_stream_str(file.file)

    # copyright Judgment
    if copyright:
        copyright = copyright.strip()
        if copyright == '':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid copyright: {copyright}"})
    # filingNo Judgment
    if filingNo:
        filingNo = filingNo.strip()
        if filingNo == '':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid filingNo: {filingNo}"})

    if any([name, file, copyright, filingNo]):
        updated = True
    else:
        updated = False

    # update
    if name:
        platform.name = name
    if file:
        # platform.logo = str(dest_path.resolve())
        platform.logo = logo
    if copyright:
        platform.copyright = copyright
    if filingNo:
        platform.filingNo = filingNo

    if updated:
        platform.updated_at = datetime.utcnow()
    # save
    platform.save()
    # reload
    platform.reload()

    data = convert_mongo_document_to_data(platform)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.get("/indexui",
            summary="Home Configuration Details")
def read_indexui(
        current_user: UserModel = Depends(deps.get_current_user)):
    data = ui_usecase.read_indexui()

    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no indexui found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.put("/indexui",
            summary="Home page configuration Modification")
def update_indexui(
        form: UiUpdateForm,
        current_user: UserModel = Depends(deps.get_current_user)):
    indexui = IndexUiModel.objects.first()
    if indexui is None:
        # If it doesn't exist，Creates a: Fields you are not sure about are left blank
        indexui = IndexUiModel(
            id=generate_uuid(length=26)
        )
        indexui.save()
        indexui.reload()

    title = form.title
    intro = form.intro
    styles_start = form.styles_start
    styles_stats = form.styles_stats
    styles_copyright = form.styles_copyright

    #
    updated = False

    # title Judgment
    if title:
        title = title.strip()
        if title == '':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid title: {title}"})
        else:
            indexui.title = title
            updated = True

    # intro Judgment
    if intro:
        intro = intro.strip()
        if intro == '':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid intro: {intro}"})
        else:
            indexui.intro = intro
            updated = True

    # styles_start
    if styles_start:
        if not isinstance(styles_start, Dict):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid styles_start: {styles_start}"})
        else:
            indexui.styles_start = styles_start
            updated = True

    # styles_stats
    if styles_stats:
        if not isinstance(styles_stats, Dict):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid styles_stats: {styles_stats}"})
        else:
            indexui.styles_stats = styles_stats
            updated = True

    # styles_copyright
    if styles_copyright:
        if not isinstance(styles_copyright, Dict):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid styles_copyright: {styles_copyright}"})
        else:
            indexui.styles_copyright = styles_copyright
            updated = True

    #
    if updated:
        indexui.updated_at = datetime.utcnow()
    # save
    indexui.save()
    # reload
    indexui.reload()

    data = convert_mongo_document_to_data(indexui)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.put("/indexui/file",
            summary="Home page configuration Modification")
def update_indexui_file(
        file: UploadFile,
        current_user: UserModel = Depends(deps.get_current_user)):
    indexui = IndexUiModel.objects.first()
    if indexui is None:
        # If it doesn't exist，Creates a: Fields you are not sure about are left blank
        indexui = IndexUiModel(
            id=generate_uuid(length=26)
        )
        indexui.save()
        indexui.reload()

    # logo Upload
    # storage_path = Path(settings.BASE_DIR, settings.CONFIGS_PATH, "indexui")
    # if not (storage_path.exists() and storage_path.is_dir()):
    #     storage_path.mkdir(parents=True)
    #
    # dest_path = Path(storage_path, file.filename)
    # # As the name file exists，Then it covers
    # # file.file is `file-like` object
    # chunked_copy(file.file, "/home/test.png")     # only for debug
    background = convert_uploaded_img_to_b64_stream_str(file.file)

    #
    indexui.update(**{
        # 'background': str(dest_path.resolve()),
        'background': background,
        'updated_at': datetime.utcnow()
    })
    indexui.save()
    indexui.reload()

    data = convert_mongo_document_to_data(indexui)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})



@router.post("/experimentui",
             summary="Experiment page configuration creation")
def create_experimentui(
        intro: str = Form(),
        current_user: UserModel = Depends(deps.get_current_user)):
    total = ExperimentUiModel.objects.count()
    if total > 0:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={"msg": "experimentui already exists, only one is allowed"})

    intro = intro.strip()
    if intro == '':
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "invalid intro for experimentui"})

    experimentui = ExperimentUiModel(
        id=generate_uuid(length=26),
        intro=intro
    )
    experimentui.save()

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success"})


@router.get("/experimentui",
            summary="Experiment page configuration details")
def read_experimentui(
        current_user: UserModel = Depends(deps.get_current_user)):
    data = ui_usecase.read_experimentui()

    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no experimentui found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.put("/experimentui",
            summary="Experiment page configuration modification")
def update_experimentui(
        intro: Optional[str] = Form(default=None),
        current_user: UserModel = Depends(deps.get_current_user)):
    experimentui = ExperimentUiModel.objects.first()

    if experimentui is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "no experimentui found"})

    intro = intro.strip()
    if intro == '':
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "invalid intro for experimentui"})

    experimentui.intro = intro
    experimentui.updated_at = datetime.utcnow()
    # save
    experimentui.save()
    # reload
    experimentui.reload()

    data = convert_mongo_document_to_data(experimentui)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.post("/skeletonui",
             summary="Profiling tool page configuration creation")
def create_skeletonui(
        intro: str = Form(),
        current_user: UserModel = Depends(deps.get_current_user)):
    total = SkeletonUiModel.objects.count()
    if total > 0:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={"msg": "skeletonui already exists, only one is allowed"})

    intro = intro.strip()
    if intro == '':
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "invalid intro for skeletonui"})

    skeletonui = SkeletonUiModel(
        id=generate_uuid(length=26),
        intro=intro
    )
    skeletonui.save()

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success"})


@router.get("/skeletonui",
            summary="Profiling tool page configuration details")
def read_skeletonui(
        current_user: UserModel = Depends(deps.get_current_user)):
    data = ui_usecase.read_skeletonui()

    if data is None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "no skeletonui found",
                                     "data": None})
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})


@router.put("/skeletonui",
            summary="Profiling tool page configuration changes")
def update_skeletonui(
        intro: Optional[str] = Form(default=None),
        current_user: UserModel = Depends(deps.get_current_user)):
    skeletonui = SkeletonUiModel.objects.first()

    if skeletonui is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "no skeletonui found"})

    intro = intro.strip()
    if intro == '':
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "invalid intro for skeletonui"})

    skeletonui.intro = intro
    skeletonui.updated_at = datetime.utcnow()
    # save
    skeletonui.save()
    # reload
    skeletonui.reload()

    data = convert_mongo_document_to_data(skeletonui)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(data)})
