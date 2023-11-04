"""
Analysis tools
"""
import copy
from datetime import datetime
from typing import List, Dict

from fastapi import (
    APIRouter,
    Depends,
    status, Form,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.models.mongo import UserModel
from app.models.mongo.deprecated import (
    CompoundStepElementInputParam_DEFAULT_DATA_MODES,
    CompoundStepElementModel,
    CompoundStepElementTypes,
    CompoundStepModel,
)
from app.schemas.deprecated import CompoundStepElementCreateSchema
from app.usecases.deprecated import compoundsteps_usecase, skeletons_usecase
from app.utils.common import convert_mongo_document_to_data

router = APIRouter()


@router.post("/",
             summary="CompoundStepElement Create")
def create_compoundstep_element(
        elementCreateSchema: CompoundStepElementCreateSchema,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    note： When manipulating elements，There are two kinds of judgments involved：
            - Reliance on legitimacy judgment
            - this element be Ref Stability judgment of

    note： ElementModel the id Generating strategies: <skeleton_id>_<compoundstep_id>_<source_id>, Among them source_id You can write as task_id or data_id.
        be Ref stability：
            - Moving up and down Task ElementModel When type，Other elements are based on (skeleton_id, source_id)，That is, it can be stably located to this skeleton In thethe Task ElementModel；
            - Moving up and down Data ElementModel When type，Other elements none Ref thisthe，No need to think about be Ref stability
        Delete ElementModel：
            - Delete Task ElementModel： According to (skeleton_id, source_id)，That is, it can be stably located to this skeleton In thethe Task ElementModel，Delete
            - Delete Data ElementModel： Because Data Reusethe，According to (skeleton_id, compoundstep_id, source_id)，Before you can locate this skeleton In thethe Data ElementModel，Delete

    - increase element

        - No matter what task or data：
            - Judgmentthe task-data Whether they appear at the same time CompoundStep：
                - YES：Not allowed，Back to Tips
                - NO： continue

        - If is task（Non-reusable）：
            - Determines that the global is not repeatable，There can only be one task： Based on task_id （Contains the judgment of the same CompoundStep the task）
            - data Dependent judgment：
                - correspondencethe data this task Above （Only consider the current CompoundStep the（Free of））： Iterate over all upstream elements， Determine if there is a correspondence data（derived_from_src_id）:
                    - YES: Not allowed，Back to Tips
                    - NO: continue
            - Based on element Information，Judgmentthe tasks_dependencies （Through the `SkeletonModel.experiment_tasks_dependencies` get）
                - Input dependencies（bethe element Not in the moment element Below）
                - be（thisthe element Not in the moment element Above）
                - Whether dependencies are broken：
                    - YES： Not allowed，Back to Tips
                    - NO： continue
            - New ElementModel， correspondencethe id Append to elements
            - Update CompoundStep the `elements` fields
            - Update SkeletonModel.tasks thecorrespondence task the `is_used=True`

        - If is data（Can span CompoundStep Reuse）：
            - Judge the same CompoundStep the data： data_id
            - correspondencethe task（across CompoundStep）：
                - YES：allow，continue
                - NO：Not allowed，Back to Tips
            - New ElementModel， correspondencethe id Append to elements
            - Update CompoundStep the `elements` fields

    :param elementCreateSchema:
    :param current_user:
    :return:
    """
    # CompoundStepModel
    compoundstep_id = elementCreateSchema.compoundstep_id
    if not compoundstep_id:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStep not found"})
    compoundStepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not compoundStepModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStep not found"})
    # SkeletonModel
    skeletonModel = compoundStepModel.skeleton
    if not skeletonModel:
        # delete dangling CompoundStepModel
        print(f"skeleton not found for dangling CompoundStepModel: {compoundstep_id}, now delete it.")
        compoundStepModel.delete()  # CompoundStepElementModel Yes CASCADE Delete
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})

    # getwith：Used for subsequent
    # elements
    current_elements = compoundStepModel.elements
    if not current_elements:
        current_elements = []
    # experiment_tasks
    experiment_tasks = skeletonModel.experiment_tasks  # List[Dict], ref: `ToolTaskForSkeletonCreationSchema`
    # experiment_tasks_datasets
    experiment_tasks_datasets = skeletonModel.experiment_tasks_datasets
    # experiment_tasks_dependencies
    experiment_tasks_dependencies = skeletonModel.experiment_tasks_dependencies

    # fields，Both of them are str
    for field, value in elementCreateSchema.dict().items():
        # loc_index： Must have int
        if field == 'loc_index':
            if not isinstance(value, int) or value < -1:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid element_{field} format: {value}"})
            else:
                continue
        if not isinstance(value, str):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid element_{field} format: {value}"})

    element_type = elementCreateSchema.type
    element_name = elementCreateSchema.name
    src_id = elementCreateSchema.src_id
    skeleton_id = elementCreateSchema.skeleton_id
    compoundstep_id = elementCreateSchema.compoundstep_id
    loc_index = elementCreateSchema.loc_index

    # upper Chemical processing
    element_type = element_type.upper()

    # Judgment element_type: Steps（TASK）/Data（file，file，Data）
    if element_type not in CompoundStepElementTypes:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid element_type: {element_type}"})

    # the source Experiment
    src_experiment = skeletonModel.experiment
    # the source Tool
    src_tool = None

    print(f"element_type: {element_type}")
    # Types：TASK
    if element_type == 'TASK':
        # Querying src_tool
        for t in experiment_tasks:
            if t.get("task_id") == src_id:
                src_tool = t.get("tool")  # str
                break
        if not src_tool:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"no source tool found for [{element_type}] `{src_id}`"})

        # - Judgmentthe task-data Whether they appear at the same time CompoundStep：
        _code, msg, is_coexist = compoundsteps_usecase.check_task_has_conjugated_data_in_same_compoundstep(
            skeleton_id=skeleton_id,
            compoundstep_id=compoundstep_id,
            src_id=src_id
        )
        if _code != status.HTTP_200_OK:
            return JSONResponse(status_code=_code, content={"msg": msg})
        else:
            if is_coexist is True:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": msg})

        #  Determines that the global is not repeatable，There can only be one task： Based on task_id （Contains the judgment of the same CompoundStep the task）
        _code, msg, has_duplicated_task = compoundsteps_usecase.check_duplicated_task_in_skeleton(
            skeleton_id=skeleton_id, src_id=src_id)
        if _code != status.HTTP_200_OK:
            return JSONResponse(status_code=_code, content={"msg": msg})
        else:
            if has_duplicated_task is True:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": msg})

        # - data Dependent judgment：
        #   - correspondencethe data this task Above （Only consider the current CompoundStep the（Free of））： Iterate over all upstream elements， Determine if there is a correspondence data（derived_from_src_id）:
        #       - YES: Not allowed，Back to Tips
        #       - NO: continue
        _code, msg, has_conjugate = compoundsteps_usecase.check_task_has_conjugated_data_in_skeleton_upstream_compoundsteps(
            skeleton_id=skeleton_id,
            compoundstep_id=compoundstep_id,
            src_id=src_id
        )
        if _code != status.HTTP_200_OK:
            return JSONResponse(status_code=_code, content={"msg": msg})
        else:
            if has_conjugate is True:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": msg})

        # - Based on element Information，Judgmentthe tasks_dependencies （Through the `SkeletonModel.experiment_tasks_dependencies` get）
        #   - Input dependencies（bethe element Not in the moment element Below）
        #   - be（thisthe element Not in the moment element Above）
        #   - Whether dependencies are broken：
        #       - YES： Not allowed，Back to Tips
        #       - NO： continue
        _code, msg, is_dependency_broken = compoundsteps_usecase.check_task_inputs_and_outputs_dependencies_well_maintained_in_skeleton(
            skeleton_id=skeleton_id,
            compoundstep_id=compoundstep_id,
            loc_index=loc_index,
            task_id=src_id
        )
        if _code != status.HTTP_200_OK:
            return JSONResponse(status_code=_code, content={"msg": msg})
        else:
            if is_dependency_broken is True:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": msg})

        # get dependency
        element_dependencies = None  # Optional[Dict]
        for d in experiment_tasks_dependencies:
            if src_id == d.get("task_id"):
                element_dependencies = copy.deepcopy(d)
                break
        if not element_dependencies:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": f"element dependency not found for {src_id}"})
        if not isinstance(element_dependencies, Dict):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid dependencies for element {src_id}"})

        # Update CompoundStepElementInputParam the `default_data_mode`
        # ref: CompoundStepElementInputParam_DEFAULT_DATA_MODES
        inputs_new = copy.deepcopy(element_dependencies.get("inputs"))
        for _input in inputs_new:
            # # Types： file/file/Data
            # if _input["type"] in ("file", "dir"):
            depend_on = _input.get("depend_on")
            if depend_on:
                if isinstance(depend_on, Dict):
                    if bool(depend_on) is True:
                        _input["default_data_mode"] = 'DEPENDENCY'
                    else:
                        _input["default_data_mode"] = 'NO_DEFAULT'
                else:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"msg": f"invalid depend_on for element input: {_input}:"})
            else:
                _input["default_data_mode"] = 'NO_DEFAULT'
            # # Types： Numeric
            # else:
            #     _input["default_data_mode"] = 'NO_DEFAULT'
            # Initialization CompoundStepElementInputParam the `display_name`
            _input["display_name"] = _input.get("name")

        # outputs
        outputs_new = copy.deepcopy(element_dependencies.get("outputs"))

        compoundStepElementModel = CompoundStepElementModel(
            id=f"{skeletonModel.id}_{compoundstep_id}_{src_id}",
            skeleton=skeletonModel,
            compoundstep=compoundStepModel,
            type=element_type,
            name=element_name,
            src_id=src_id,
            derived_from_src_id=None,
            derived_from_src_name=None,
            derived_from_output_name=None,
            src_experiment=src_experiment,
            src_tool=src_tool,
            inputs=inputs_new,
            outputs=outputs_new
        )
        compoundStepElementModel.save()
        compoundStepElementModel.reload()
        #
        if loc_index == -1:
            current_elements.append(compoundStepElementModel.id)
        else:
            current_elements.insert(loc_index, compoundStepElementModel.id)
        # Update CompoundStep the `elements` fields
        compoundStepModel.elements = current_elements
        compoundStepModel.updated_at = datetime.utcnow()
        compoundStepModel.save()
        # Update SkeletonModel.tasks thecorrespondence task the `is_used=True`
        experiment_tasks = skeletonModel.experiment_tasks
        for t in experiment_tasks:
            if t.get("task_id") == src_id:
                t["is_used"] = True
        skeletonModel.experiment_tasks = experiment_tasks
        skeletonModel.updated_at = datetime.utcnow()
        skeletonModel.save()
        skeletonModel.reload()
        # Return
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})

    # Types：DATA
    else:
        # It's just that Data Types， get:
        #   - data the task_id: `derived_src_id`
        #   - data the task correspondencethe tool: `src_tool`
        derived_from_src_id = None
        derived_from_src_name = None
        for dataset in experiment_tasks_datasets:
            # Querying：derived_src_id
            # （Each data dictionary，the id，It could be _id，see Skeleton Createwhen， experiment_tasks_datasets the）
            # JudgmentCondition:
            #   data_type = taskData when： with _id
            #   data_type != taskData when, with id
            dt_id = dataset.get("id") or dataset.get("_id")
            if dt_id == src_id:
                # Data
                if (dataset.get("is_memory") is True) or (dataset.get("mark") == "structure"):
                    derived_from_src_id = dataset.get("id").split("_")[1]
                # file/file：with DataFileSystem，Yes task_id
                else:
                    derived_from_src_id = dataset.get("task_id")
                print(f"derived_from_src_id: {derived_from_src_id}")
                # Querying：src_tool
                # traversal experiment_tasks
                for t in experiment_tasks:
                    if t.get("task_id") == derived_from_src_id:
                        derived_from_src_name = t.get("task_name")  # ref: experiment_tasks the
                        src_tool = t.get("tool")  # str
                        break
        if not derived_from_src_id:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"no source task found for data [{src_id}]"})
        if not src_tool:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"no source tool found for data [{src_id}]"})

        # Judge the same CompoundStep the data： data_id
        _code, msg, duplicated = compoundsteps_usecase.check_duplicated_data_in_compoundstep(
            compoundstep_id=compoundstep_id,
            src_id=src_id
        )
        if _code != status.HTTP_200_OK:
            return JSONResponse(status_code=_code, content={"msg": msg})
        else:
            if duplicated is True:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": msg})

        # - Judgmentthe task-data Whether they appear at the same time CompoundStep：
        _code, msg, is_coexist = compoundsteps_usecase.check_data_has_conjugated_task_in_same_compoundstep(
            skeleton_id=skeleton_id,
            compoundstep_id=compoundstep_id,
            src_id=src_id,
            derived_from_src_id=derived_from_src_id
        )
        if _code != status.HTTP_200_OK:
            return JSONResponse(status_code=_code, content={"msg": msg})
        else:
            if is_coexist is True:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": msg})

        # Judgmentcorrespondencethe task（across CompoundStep）
        _code, msg, has_conjugate = compoundsteps_usecase.check_data_has_conjugated_task_in_upstream_compoundsteps(
            skeleton_id=skeleton_id,
            current_compoundstep_id=compoundstep_id,
            src_id=src_id,
            derived_from_src_id=derived_from_src_id
        )
        if _code != status.HTTP_200_OK:
            return JSONResponse(status_code=_code, content={"msg": msg})
        else:
            # the task：Not allowed
            if has_conjugate is False:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"msg": msg})

        # derived_from_output_name (Premise： the task)
        derived_from_output_name = None
        expt_tasks = skeletonModel.experiment_tasks  # List[Dict]
        for expt_task in expt_tasks:
            if expt_task.get("task_id") == derived_from_src_id:
                expt_task_outputs = expt_task.get("outputs")
                for expt_task_output in expt_task_outputs:
                    # AttributeError: 'BaseList' object has no attribute 'get'
                    output_data = expt_task_output.get("data", {})
                    # data_id: note DataFileSystem with id，No _id
                    # if output_data.get("_id") == src_id:
                    if output_data.get("id") == src_id:
                        derived_from_output_name = expt_task_output.get("name")
                        break
        # New
        compoundStepElementModel = CompoundStepElementModel(
            id=f"{skeletonModel.id}_{compoundstep_id}_{src_id}",
            skeleton=skeletonModel,
            compoundstep=compoundStepModel,
            type=element_type,
            name=element_name,
            src_id=src_id,
            derived_from_src_id=derived_from_src_id,
            derived_from_src_name=derived_from_src_name,
            derived_from_output_name=derived_from_output_name,
            src_experiment=src_experiment,
            src_tool=src_tool,
            inputs=None,
            outputs=None
        )
        compoundStepElementModel.save()
        compoundStepElementModel.reload()
        #
        if loc_index == -1:
            current_elements.append(compoundStepElementModel.id)
        else:
            current_elements.insert(loc_index, compoundStepElementModel.id)
        # Update CompoundStep the `elements` fields
        compoundStepModel.elements = current_elements
        compoundStepModel.updated_at = datetime.utcnow()
        compoundStepModel.save()
        # Return
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})


@router.get("/{element_id}",
            summary=" CompoundStepElement Details")
def read_compoundstep_element(
        element_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Update Task Element the the：
        -

    :param element_id:
    :param element_input_update_form:
    :param current_user:
    :return:
    """
    # Judgment Element
    elementModel = CompoundStepElementModel.objects(id=element_id).first()
    if not elementModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStepElementModel not found: {element_id}"})

    data = convert_mongo_document_to_data(elementModel)
    #
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(data))


@router.put("/{element_id}",
            summary="CompoundStepElement Update")
def update_compoundstep_element(
        element_id: str,
        input_name: str = Form(),
        display_name: str = Form(default=None),
        default_data_mode: str = Form(default=None),
        is_display: bool = Form(default=None),
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Update Task Element the the：
        -

    :param element_id:
    :param input_name:
    :param display_name:
    :param default_data_mode:
    :param is_display:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase.check_if_skeleton_editable(pk=element_id, pk_type='CompoundStepElement')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # Judgment Element
    elementModel = CompoundStepElementModel.objects(id=element_id).first()
    if not elementModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStepElementModel not found: {element_id}"})
    # Judgment Element type： Update TASK Types
    element_type = elementModel.type
    if element_type not in CompoundStepElementTypes:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"CompoundStepElementModel has invalid type: {element_type}"})

    # Must have
    if not input_name:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"missing input_name"})
    # Judgment： default_data_mode
    if default_data_mode:
        if default_data_mode not in CompoundStepElementInputParam_DEFAULT_DATA_MODES:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid default_data_mode: {default_data_mode}"})

    # Judgment is_display
    if is_display is not None:
        if not isinstance(is_display, bool):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid is_display: {is_display}"})

    # inputs
    inputs = elementModel.inputs
    if not isinstance(inputs, List):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"CompoundStepElementModel has invalid inputs: {inputs}"})
    # Judgment
    is_input_found = False
    for _input in inputs:
        if _input.get("name") == input_name:
            if default_data_mode:
                _input["default_data_mode"] = default_data_mode
            if display_name:
                _input["display_name"] = display_name
            if is_display is not None:
                _input["is_display"] = is_display

            # Update
            elementModel.inputs = inputs
            elementModel.updated_at = datetime.utcnow()
            elementModel.save()
            elementModel.reload()
            #
            is_input_found = True
            #
            break

    if is_input_found is False:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStepElementModel.inputs has no: {input_name}"})
    #
    data = convert_mongo_document_to_data(elementModel)
    #
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(data))


@router.delete("/{element_id}",
               summary="CompoundStepElement Delete")
def delete_compoundstep_element(
        element_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    note： When manipulating elements，There are two kinds of judgments involved：
            - Reliance on legitimacy judgment
            - this element be Ref Stability judgment of

    note： ElementModel the id Generating strategies: <skeleton_id>_<compoundstep_id>_<source_id>, Among them source_id You can write as task_id or data_id.
        be Ref stability：
            - Moving up and down Task ElementModel When type，Other elements are based on (skeleton_id, source_id)，That is, it can be stably located to this skeleton In thethe Task ElementModel；
            - Moving up and down Data ElementModel When type，Other elements none Ref thisthe，No need to think about be Ref stability
        Delete ElementModel：
            - Delete Task ElementModel： According to (skeleton_id, source_id)，That is, it can be stably located to this skeleton In thethe Task ElementModel，Delete
            - Delete Data ElementModel： Because Data Reusethe，According to (skeleton_id, compoundstep_id, source_id)，Before you can locate this skeleton In thethe Data ElementModel，Delete


    - Delete element
        - If is task：
            - Judgment（across CompoundStep） Is there a link? data：
                - YES： Not allowed，Back to Tips
                - NO： continue
            - Delete Element
            - Update CompoundStep.elements Lists，Remove the corresponding Element the id
            - Update Skeleton.tasks In the correspondence task.is_used = False

        - If is data：
            - Delete Element
            - Update CompoundStep.elements Lists，Remove the corresponding Element the id


    :param element_id:
    :param current_user:
    :return:
    """
    # Judgment Skeleton Editable or not
    code, msg, editable = skeletons_usecase.check_if_skeleton_editable(pk=element_id, pk_type='CompoundStepElement')
    if editable is False:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"msg": msg})

    # Judgment Element
    elementModel = CompoundStepElementModel.objects(id=element_id).first()
    if not elementModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"CompoundStepElementModel not found: {element_id}"})
    # Judgment Element type
    element_type = elementModel.type
    if element_type not in CompoundStepElementTypes:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"CompoundStepElementModel has invalid type: {element_type}"})
    # the Skeleton
    skeletonModel = elementModel.skeleton
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"relevant SkeletonModel not found for element: {element_id}"})

    # the CompoundStep
    compoundstepModel = elementModel.compoundstep
    if not compoundstepModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"relevant CompoundStepModel not found for element: {element_id}"})

    # Judgment CompoundStep.elements
    elements = compoundstepModel.elements
    if not isinstance(elements, List):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "msg": f"relevant CompoundStepModel [{compoundstepModel.id}] has invalid elements: {elements}"})
    if element_id not in elements:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "msg": f"element `{element_id}` not in relevant CompoundStepModel.elements: {elements}"})

    # - If is task：
    #   - Judgment（across CompoundStep） Is there a link? data：
    #       - YES： Not allowed，Back to Tips
    #       - NO： continue
    if elementModel.type == 'TASK':
        # Querying Data Typesthe Element，withJudgment; Just take one
        # Condition Data Element.derived_from_src_id = Task Element.src_id
        relevantDataElement = CompoundStepElementModel.objects(
            skeleton=skeletonModel.id,
            derived_from_src_id=elementModel.src_id,
            type__ne="TASK"
        ).first()
        if relevantDataElement:
            # msg = f"forbidden to delete: TASK CompoundStepElementModel [{element_id}] has relevant DATA in CompoundStep [{relevantDataElement.compoundstep.name}]"
            msg = f"Delete：Steps CompoundStep [{relevantDataElement.compoundstep.name}] In theData [{relevantDataElement.name}]"
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"forbidden to delete: TASK CompoundStepModel [{element_id}] has relevant DATA in CompoundStep [{relevantDataElement.compoundstep.name}]"})

    # Delete Element
    try:
        elementModel.delete()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to delete CompoundStepElementModel `{element_id}`: {e}"})

    # Update CompoundStep.elements Lists，Remove the corresponding Element the id
    elements = [i for i in elements if i != element_id]
    #
    compoundstepModel.elements = elements
    compoundstepModel.updated_at = datetime.utcnow()
    compoundstepModel.save()

    # If the Task Typesthe Element
    # Update Skeleton.tasks In the correspondence task.is_used = False
    if elementModel.type == 'TASK':
        expt_tasks = skeletonModel.experiment_tasks  # List[Dict]
        for expt_task in expt_tasks:
            # note：with Element the src_id
            if expt_task.get("task_id") == elementModel.src_id:
                # Update
                expt_task["is_used"] = False
                skeletonModel.experiment_tasks = expt_tasks
                skeletonModel.updated_at = datetime.utcnow()
                skeletonModel.save()
                break
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success"})
