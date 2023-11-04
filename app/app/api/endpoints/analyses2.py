"""
Analysis based on analysis tools
"""

from datetime import datetime
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
    AnalysisModel2,
    SkeletonModel2,
    UserModel,
)
from app.schemas import (
    Analysis2CreateSchema,
    Analysis2UpdateSchema
)
from app.usecases import analyses_usecase2
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES

router = APIRouter()


@router.post("/",
             summary="Analysis creation")
def create_analysis(
        createSchema: Analysis2CreateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    note：Because it involves a trial run，Therefore, no verification is required Skeleton state

    :param createSchema:
    :param current_user:
    :return:
    """
    is_trial = createSchema.is_trial
    if not isinstance(is_trial, bool):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid is_trial: {is_trial}"})

    skeleton_id = createSchema.skeleton
    if not skeleton_id:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid skeleton_id: {skeleton_id}"})

    # Same user，One tool：Only one is allowed state=READY Analysis of, Return directly
    analysisModel = AnalysisModel2.objects(skeleton=skeleton_id, user=current_user.id, state='READY').first()
    if analysisModel:
        data = convert_mongo_document_to_data(analysisModel)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=jsonable_encoder(data))

    # skeleton
    skeletonModel = SkeletonModel2.objects(id=skeleton_id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"skeleton not found for skeleton_id: {skeleton_id}"})
    # Create Analysis
    try:
        analysisModel = AnalysisModel2(
            id=generate_uuid(length=26),
            is_trial=is_trial,
            skeleton=skeletonModel,
            user=current_user,
            name=createSchema.name,
            description=createSchema.description,
            dag=skeletonModel.dag,
            inputs_config=skeletonModel.inputs_config,
            outputs_config=skeletonModel.outputs_config,
            inputs=skeletonModel.inputs,
            outputs=skeletonModel.outputs
        )
        analysisModel.save()
        analysisModel.reload()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to create analysis for skeleton: {skeletonModel.id}"})
    #
    data = convert_mongo_document_to_data(analysisModel)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.get("/",
            summary="List of analyses")
def read_analyses(
        is_trial: Union[bool, None] = None,
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

    :param is_trial:
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
    content = analyses_usecase2.read_analyses(
        is_trial=is_trial,
        name=name,
        creator=creator,
        skeleton_id=skeleton_id,
        state=state,
        page=page,
        size=size,
        viewer=current_user,
        only_own=True,  # You can only see your own
        sort=sort
    )
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/{analysis_id}",
            summary="Analysis details")
def read_analysis(
        analysis_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param analysis_id:
    :param current_user:
    :return:
    """

    analysisModel = AnalysisModel2.objects(id=analysis_id).first()
    if not analysisModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisModel not found for: {analysis_id}"})

    analysis_data = analyses_usecase2.read_analysis(
        analysis_id=analysisModel.id
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(analysis_data))


@router.put("/{analysis_id}",
            summary="Analysis editor")
def update_analysis(
        analysis_id: str,
        update: Analysis2UpdateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param analysis_id:
    :param update:
    :param current_user:
    :return:
    """

    # It has to be yourself.
    analysisModel = AnalysisModel2.objects(
        id=analysis_id,
        user=current_user.id
    ).first()
    if not analysisModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisModel not found for: {analysis_id}"})

    # identifier
    updated = False

    # All updated information：Free of logo（file Types）
    updates = {
        "name": update.name,
        "description": update.description,
        "inputs": update.inputs,
        "outputs": update.outputs,
        "state": update.state
    }
    updates = {k: v for k, v in updates.items() if v not in INVALID_UPDATE_VALUE_TYPES}
    if updates != dict():
        analysisModel.update(**updates)
        # identifier
        updated = True

    # Update time，And save it
    if updated is True:
        analysisModel.updated_at = datetime.utcnow()
        analysisModel.save()

    # Read the updated information
    analysis_data = analyses_usecase2.read_analysis(
        analysis_id=analysisModel.id
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(analysis_data))


@router.delete("/{analysis_id}",
               summary="Analyze deletion")
def delete_analysis(
        analysis_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param analysis_id:
    :param current_user:
    :return:
    """

    # It has to be yourself.
    analysisModel = AnalysisModel2.objects(
        id=analysis_id,
        user=current_user.id
    ).first()
    if not analysisModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisModel not found for: {analysis_id}"})

    analysis_data = analyses_usecase2.read_analysis(
        analysis_id=analysisModel.id,
    )

    # FIXME: Determine whether or not Pending
    #   - YES： Disallow deletion
    #   - NO： Allow deletion
    state = analysisModel.state
    if state == 'PENDING':
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"analysisModel has pending step, forbidden to delete."})
    else:
        analysisModel.delete()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})
