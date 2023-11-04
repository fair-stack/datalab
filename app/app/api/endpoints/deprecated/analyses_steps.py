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
from app.forms.deprecated import AnalysisStepUpdateForm
from app.models.mongo import UserModel
from app.models.mongo.deprecated import (
    AnalysisStepElementModel,
    AnalysisStepModel,
)
from app.usecases.deprecated import analysis_step_elements_usecase
from app.utils.common import convert_mongo_document_to_data
from app.utils.constants import ANALYSIS_STEP_STATES

router = APIRouter()


@router.get("/{step_id}",
            summary="Analysis Step Details")
def read_analysis_step(
        step_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param step_id:
    :param current_user:
    :return:
    """

    analysisStepModel = AnalysisStepModel.objects(id=step_id).first()
    if not analysisStepModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisStepModel not found for: {step_id}"})

    analysis_step_data = convert_mongo_document_to_data(analysisStepModel)

    # AnalysisStepModel.elements
    element_data_list = []
    element_id_list = analysisStepModel.elements     # List[str]
    if isinstance(element_id_list, List):
        for element_id in element_id_list:
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
            element_data = convert_mongo_document_to_data(elementModel)
            element_data_list.append(element_data)
    # substitution steps
    analysis_step_data["elements"] = element_data_list

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(analysis_step_data))


@router.put("/{step_id}",
            summary="Analysis Step Update")
def update_analysis_step(
        step_id: str,
        step_update_form: AnalysisStepUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param step_id:
    :param step_update_form:
    :param current_user:
    :return:
    """

    analysisStepModel = AnalysisStepModel.objects(id=step_id).first()
    if not analysisStepModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisStepModel not found for: {step_id}"})

    state = step_update_form.state
    if state:
        if state not in ANALYSIS_STEP_STATES:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid state `{state}` for analysisStepModel"})
        else:
            analysisStepModel.update(**{
                'state': state,
                'updated_at': datetime.utcnow()
            })
            analysisStepModel.save()
            analysisStepModel.reload()

            # Refresh correspondence analysis the state： the step They all succeed，And then analysis To be regarded as`Done`，otherwise`Done`
            steps_states = []
            analysisModel = analysisStepModel.analysis
            step_ids = analysisModel.steps  # List[str]
            if isinstance(step_ids, List):
                for step_id in step_ids:
                    analysisStepModel = AnalysisStepModel.objects(id=step_id).first()
                    if not analysisStepModel:
                        steps_states.append(None)
                        continue
                    else:
                        _state = analysisStepModel.state or None
                        steps_states.append(_state)

                # state
                _state = "COMPLETED"
                for state in steps_states:
                    # the step They all succeed，And then analysis To be regarded as`Done`，otherwise`Done`
                    if state != 'SUCCESS':
                        _state = "INCOMPLETED"
                        break
                #
                analysisModel.update(**{
                    'state': _state,
                    'updated_at':datetime.utcnow()
                })
                analysisModel.save()
            #
            analysis_step_data = convert_mongo_document_to_data(analysisStepModel)
            return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(analysis_step_data))
