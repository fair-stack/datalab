"""
Deprecated:
Analysis based on analysis tools
"""

from datetime import datetime
from typing import List, Union

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.forms.deprecated import AnalysisUpdateForm
from app.models.mongo import UserModel
from app.models.mongo.deprecated import (
    AnalysisStepElementModel,
    AnalysisModel,
    AnalysisStepModel,
    CompoundStepElementModel,
    CompoundStepModel,
    SkeletonModel,
)
from app.schemas.deprecated import (
    AnalysisCreateSchema,
)
from app.usecases.deprecated import analyses_usecase
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES

router = APIRouter()


@router.post("/",
             summary="Analysis creation")
def create_analysis(
        createSchema: AnalysisCreateSchema,
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
    # skeleton
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"skeleton not found for skeleton_id: {skeleton_id}"})
    # Create Analysis
    analysisModel = AnalysisModel(
        id=generate_uuid(length=26),
        is_trial=is_trial,
        skeleton=skeletonModel,
        user=current_user,
        name=createSchema.name,
        description=createSchema.description
        # steps=[]   # For the time being[], Create [AnalysisStep] after，Update this field
    )
    analysisModel.save()
    analysisModel.reload()

    # skeleton.compoundsteps
    compoundStepModel_list = []
    compoundstep_ids = skeletonModel.compoundsteps
    if (not compoundstep_ids) or (not isinstance(compoundstep_ids, List)) or (len(compoundstep_ids) == 0):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid skeleton_compoundsteps: {compoundstep_ids}"})
    for _id in compoundstep_ids:
        compoundStepModel = CompoundStepModel.objects(id=_id).first()
        if not compoundStepModel:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"compoundstepModel not found for: {_id}"})
        compoundStepModel_list.append(compoundStepModel)

    # Create [AnalysisStep]
    try:
        stepModel_list = []
        # Must be maintained compoundstep The order of
        for compoundStepModel in compoundStepModel_list:
            stepModel = AnalysisStepModel(
                id=generate_uuid(length=26),
                compoundstep=compoundStepModel,
                analysis=analysisModel,
                name=compoundStepModel.name,
                description=compoundStepModel.description,
                instruction=compoundStepModel.instruction,
                multitask_mode=compoundStepModel.multitask_mode
                # elements=[]     # For the time being，Create [AnalysisStepElement] (According to CompoundStep.elements) after，Update this field
            )
            stepModel.save()
            stepModel.reload()
            # Add
            stepModel_list.append(stepModel)
    except Exception as e:
        print(e)
        # An error has occurred.： Create
        for stepModel in stepModel_list:
            stepModel.delete()
    else:
        # Update analysisModel.steps
        analysisModel.steps = [s.id for s in stepModel_list]
        analysisModel.updated_at = datetime.utcnow()
        analysisModel.save()
        analysisModel.reload()

    # Create [AnalysisStepElement]
    for stepModel in stepModel_list:
        compoundStepModel = stepModel.compoundstep  # str
        compoundStepModel_element_id_list = compoundStepModel.elements
        # traversal compoundStepModel_element_id_list， Create [AnalysisStepElement]
        try:
            elementModel_list = []
            for element_id in compoundStepModel_element_id_list:
                compoundStepElementModel = CompoundStepElementModel.objects(id=element_id).first()
                if not compoundStepElementModel:
                    # Create
                    for elementModel in elementModel_list:
                        elementModel.delete()
                    #
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"msg": f"compoundStepElementModel not found for: {element_id}"})
                else:
                    # # JudgmentYes or noCreate AnalysisStepElementModel： Based on having uniqueness compoundstep_element
                    # elementModel = AnalysisStepElementModel.objects(compoundstep_element=element_id).first()
                    # if elementModel:
                    #     print(f"analysisStepElementModel already created before: {element_id}")
                    #     # Add
                    #     elementModel_list.append(elementModel)
                    #     continue

                    # preprocessing： inputs， outputs
                    # print(f"compoundStepElementModel: {convert_mongo_document_to_data(compoundStepElementModel)}")
                    compoundStepElementModel_inputs = compoundStepElementModel.inputs
                    compoundStepElementModel_outputs = compoundStepElementModel.outputs
                    # Only for TASK: Because only TASK The type has inputs and outputs
                    if compoundStepElementModel.type == 'TASK':
                        # inputs preprocessing: traversalJudgment CompoundStepElementModel.inputs.input Inside： Yes or no default_data_mode = NO_DEFAULT, DEPENDENCY
                        #   - YES： Inside `data`，Retain other information
                        #   - NO： Don't do anything with it
                        if isinstance(compoundStepElementModel_inputs, List):
                            for _input in compoundStepElementModel_inputs:
                                # See Synonyms at： CompoundStepElementInputParam_DEFAULT_DATA_MODES
                                #   - Numeric input：
                                #       - NO_DEFAULT: User input，Therefore, the cleaning analysis tool is brought over data
                                #       - DEFAULT_DATA： Keep what comes with the analysis tools data
                                #   - File type/In-memory data input：
                                #       - NO_DEFAULT: The user chooses the data himself，Therefore, the cleaning analysis tool is brought over data
                                #       - DEPENDENCY： Using dependent data，Still clean up the analysis tool to bring data，afterAccording to depend_on Take a value
                                if _input.get("default_data_mode") in ['NO_DEFAULT', 'DEPENDENCY']:
                                    _input['data'] = None
                                # Remove redundant information： {"_cls": "CompoundStepElementOutputData", xxx}
                                _input.pop("_cls", None)

                        # outputs preprocessing: traversal CompoundStepElementModel.outputs.output Inside `data`，Retain other information
                        if isinstance(compoundStepElementModel_outputs, List):
                            for output in compoundStepElementModel_outputs:
                                output['data'] = None
                                # Remove redundant information： {"_cls": "CompoundStepElementOutputData", xxx}
                                output.pop("_cls", None)

                    # id Generation strategy of： <analysis>_<analysis_step>_<src>
                    elementModel = AnalysisStepElementModel(
                        id=f"{analysisModel.id}_{stepModel.id}_{compoundStepElementModel.src_id}",
                        compoundstep_element=compoundStepElementModel,
                        analysis=analysisModel,
                        analysis_step=stepModel,
                        type=compoundStepElementModel.type,
                        name=compoundStepElementModel.name,
                        src_id=compoundStepElementModel.src_id,
                        derived_from_src_id=compoundStepElementModel.derived_from_src_id,
                        derived_from_src_name=compoundStepElementModel.derived_from_src_name,
                        derived_from_output_name=compoundStepElementModel.derived_from_output_name,
                        src_tool=compoundStepElementModel.src_tool,
                        inputs=compoundStepElementModel_inputs,
                        outputs=compoundStepElementModel_outputs,
                    )
                    elementModel.save()
                    elementModel.reload()
                    # Add
                    elementModel_list.append(elementModel)
        except Exception as e:
            print(e)
            # An error has occurred.： Create
            for elementModel in elementModel_list:
                elementModel.delete()
        else:
            # Update analysisStepModel.elements
            stepModel.elements = [t.id for t in elementModel_list]
            stepModel.updated_at = datetime.utcnow()
            stepModel.save()
            stepModel.reload()
    #
    data = convert_mongo_document_to_data(analysisModel)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


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

    analysisModel = AnalysisModel.objects(id=analysis_id).first()
    if not analysisModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisModel not found for: {analysis_id}"})

    analysis_data = analyses_usecase.read_analysis(
        analysis_id=analysisModel.id,
        with_steps_data=True,
        with_steps_states=True,
        with_elements_data=True
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(analysis_data))


@router.put("/{analysis_id}",
            summary="Analysis editor")
def update_analysis(
        analysis_id: str,
        update_form: AnalysisUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param analysis_id:
    :param update_form:
    :param current_user:
    :return:
    """

    # It has to be yourself.
    analysisModel = AnalysisModel.objects(
        id=analysis_id,
        user=current_user.id
    ).first()
    if not analysisModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisModel not found for: {analysis_id}"})

    # identifier
    updated = False

    # Update：Free of logo（file Types）
    updates = {
        "name": update_form.name,
        "description": update_form.description,
    }
    updates = {k: v for k, v in updates.items() if v not in INVALID_UPDATE_VALUE_TYPES}
    if updates != dict():
        analysisModel.update(**updates)
        # identifier
        updated = True

    # Update，And save it
    if updated is True:
        analysisModel.updated_at = datetime.utcnow()
        analysisModel.save()

    # Updateafter
    analysis_data = analyses_usecase.read_analysis(
        analysis_id=analysisModel.id,
        with_steps_data=True,
        with_steps_states=True,
        with_elements_data=True
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
    analysisModel = AnalysisModel.objects(
        id=analysis_id,
        user=current_user.id
    ).first()
    if not analysisModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"analysisModel not found for: {analysis_id}"})

    analysis_data = analyses_usecase.read_analysis(
        analysis_id=analysisModel.id,
        with_steps_data=True,
        with_steps_states=True,
        with_elements_data=False
    )

    # Judgment steps State: Yes or no Pending，
    #   - YES： Disallow deletion
    #   - NO： Allow deletion
    steps_states = analysis_data.get("steps_states")
    has_pending = False
    for state in steps_states:
        # ref: `constants.ANALYSIS_STEP_STATES`
        if state.upper() == "PENDING":
            has_pending = True
            break
    if has_pending is True:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"analysisModel has appending step, forbidden to delete."})
    else:
        analysisModel.delete()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})
