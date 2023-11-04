from typing import Dict, List

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.models.mongo.deprecated import AnalysisStepElementModel
from app.models.mongo import UserModel
from app.schemas.deprecated import AnalysisStepElementUpdateSchema
from app.usecases.deprecated import analysis_step_elements_usecase
from app.utils.common import convert_mongo_document_to_data
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES

router = APIRouter()


@router.get("/{element_id}",
            summary="Analysis StepElement Details")
def read_analysis_step_element(
        element_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param element_id:
    :param current_user:
    :return:
    """
    elementModel = AnalysisStepElementModel.objects(id=element_id).first()
    if not elementModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisStepElementModel not found for: {element_id}"})

    # Task Element： Check if input arguments depend on upstream，If，Pull the latest dependency data
    if elementModel.type == 'TASK':
        analysis_id = elementModel.analysis.id
        analysis_step_elements_usecase.get_data_for_task_element_inputs_from_dependent_element_outputs(
            analysis_id=analysis_id,
            element_id=element_id,
            with_do_update=True  # Synchronously updating data
        )

    # Data Element： Let's update the current Data Element the `data`
    else:
        analysis_id = elementModel.analysis.id
        analysis_step_elements_usecase.get_data_for_non_task_element_from_dependent_element_output(
            analysis_id=analysis_id,
            element_id=element_id,
            with_do_update=True  # Synchronously updating data
        )


    #
    data = convert_mongo_document_to_data(elementModel)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(data))


@router.put("/{element_id}",
            summary="Analysis StepElement Update")
def update_analysis_step_element(
        element_id: str,
        update_schema: AnalysisStepElementUpdateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param element_id:
    :param update_schema:
    :param current_user:
    :return:
    """

    analysisStepElementModel = AnalysisStepElementModel.objects(id=element_id).first()
    if not analysisStepElementModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisStepElementModel not found for: {element_id}"})

    #
    updates = {
        "data": update_schema.data,
        "inputs": update_schema.inputs,
        "outputs": update_schema.outputs,
        "is_selected": update_schema.is_selected,
        "state": update_schema.state
    }
    updates = {k: v for k, v in updates.items() if v not in INVALID_UPDATE_VALUE_TYPES}

    # Judgment inputs
    inputs = updates.get("inputs")
    if inputs and not isinstance(inputs, List):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid inputs format for updating analysisStepElementModel: {inputs}"})
    # Judgment outputs
    outputs = updates.get("outputs")
    if outputs and not isinstance(outputs, List):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid outputs format for updating analysisStepElementModel: {outputs}"})

    # Judgment is_selected
    is_selected = updates.get("is_selected")
    if (is_selected is not None) and (not isinstance(is_selected, bool)):
        if outputs and not isinstance(outputs, Dict):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "msg": f"invalid is_selected format for updating analysisStepElementModel: {is_selected}"})

    # Judgment state
    state = updates.get("state")
    if (not isinstance(state, str)) or ( state.upper() not in ["UNUSED", "SUCCESS", "ERROR", "PENDING"]):
        if outputs and not isinstance(outputs, Dict):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "msg": f"invalid is_selected format for updating analysisStepElementModel: {is_selected}"})
    #
    analysisStepElementModel.update(**updates)
    analysisStepElementModel.save()
    #
    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})
