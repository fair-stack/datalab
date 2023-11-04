"""
Analysis tools
"""
from datetime import datetime
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.forms.deprecated import CompoundStepUpdateForm
from app.models.mongo import UserModel
from app.models.mongo.deprecated import (
    CompoundStepModel,
    SkeletonModel,
)
from app.schemas.deprecated import (
    CompoundStepCreateSchema,
    CompoundStepSchema,
)
from app.usecases.deprecated import compoundsteps_usecase, skeletons_usecase
from app.utils.common import generate_uuid
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES, SKELETON_COMPOUNDSTEPS_MULTITASK_MODES

router = APIRouter()


@router.post("/",
             summary="CompoundStep Create")
def create_compoundstep(
        compoundStepCreateSchema: CompoundStepCreateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param compoundStepCreateSchema:
    :param current_user:
    :return:
    """

    skeleton_id = compoundStepCreateSchema.skeleton
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"skeleton not found: {skeleton_id}"})

    try:
        # New CompoundStep
        compoundStepSchema = CompoundStepSchema(**compoundStepCreateSchema.dict(),
                                                id=generate_uuid(length=26),
                                                multitask_mode='ALL',  #
                                                elements=[]
                                                )
        compoundStepModel = CompoundStepModel(**compoundStepSchema.dict())
        compoundStepModel.save()
        compoundStepModel.reload()

        # Update Skeleton
        compoundsteps = skeletonModel.compoundsteps
        if compoundsteps is None:
            compoundsteps = []
        if not isinstance(compoundsteps, List):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid compoundsteps of skeleton: {compoundsteps}"})
        # Update Skeleton the `compoundsteps`： append Newthe CompoundStep_id
        # append
        compoundsteps.append(compoundStepModel.id)
        # Update
        skeletonModel.compoundsteps = compoundsteps
        skeletonModel.updated_at = datetime.utcnow()
        skeletonModel.save()

    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": "failed to create CompoundStep: {e}"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=jsonable_encoder(compoundStepSchema.dict()))


@router.get("/{compoundstep_id}",
            summary="CompoundStep Details")
def read_compoundstep(
        compoundstep_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param compoundstep_id:
    :param compoundstep_update_form:
    :param current_user:
    :return:
    """
    code, msg, data = compoundsteps_usecase.read_compoundstep(compoundstep_id=compoundstep_id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.put("/{compoundstep_id}",
            summary="CompoundStep Update")
def update_compoundstep(
        compoundstep_id: str,
        compoundstep_update_form: CompoundStepUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param compoundstep_id:
    :param compoundstep_update_form:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase.check_if_skeleton_editable(pk=compoundstep_id, pk_type='CompoundStep')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    #
    compoundStepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not compoundStepModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStepModel not found"})

    # identifier
    updated = False

    # Update：Free of logo（file Types）
    updates = {
        "name": compoundstep_update_form.name,
        "description": compoundstep_update_form.description,
        "instruction": compoundstep_update_form.instruction,
        "multitask_mode": compoundstep_update_form.multitask_mode
    }
    updates = {k: v for k, v in updates.items() if v not in INVALID_UPDATE_VALUE_TYPES}

    # Judgment multitask_mode
    if ("multitask_mode" in updates) and (updates.get("multitask_mode") not in SKELETON_COMPOUNDSTEPS_MULTITASK_MODES):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid multitask_mode: {updates.get('multitask_mode')}"})

    if updates != dict():
        compoundStepModel.update(**updates)
        # identifier
        updated = True

    # Update，And save it
    if updated is True:
        compoundStepModel.updated_at = datetime.utcnow()
        compoundStepModel.save()

    # Updatethe
    code, msg, data = compoundsteps_usecase.read_compoundstep(compoundstep_id=compoundstep_id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.delete("/{compoundstep_id}",
               summary="CompoundStep Delete")
def delete_compoundstep(
        compoundstep_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    - Delete CompoundStep
    - Update Skeleton

    :param compoundstep_id:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase.check_if_skeleton_editable(pk=compoundstep_id, pk_type='CompoundStep')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # CompoundStepModel
    compoundStepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not compoundStepModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStep not found"})
    # SkeletonModel
    skeletonModel = compoundStepModel.skeleton
    if not skeletonModel:
        # delete dangling CompoundStepModel
        print(f"skeleton not found for dangling CompoundStepModel: {compoundstep_id}, now delete it.")
        compoundStepModel.delete()
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})

    # elements
    current_elements = compoundStepModel.elements
    if isinstance(current_elements, List):
        if len(current_elements) > 0:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "msg": f"CompoundStep not empty, forbidden to delete, please first delete elements"})
        else:
            compoundStepModel.delete()
            # Update Skeleton
            compoundsteps = skeletonModel.compoundsteps
            compoundsteps = [_id for _id in compoundsteps if _id != compoundstep_id]
            skeletonModel.compoundsteps = compoundsteps
            skeletonModel.updated_at = datetime.utcnow()
            skeletonModel.save()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})
