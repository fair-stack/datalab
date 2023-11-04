from datetime import datetime
from typing import Dict, Tuple, Any, List

from fastapi import status

from app.models.mongo.deprecated import AnalysisStepElementModel


def get_dependent_data_from_element_output(
        analysis_id: str,
        src_id: str,
        output_name: str) -> Tuple[int, str, Any]:
    """
    Fetching dependent data：
        - right Task Types： Depending on someone upstream Task An output of
        - right Data Types： Depending on someone upstream Task An output of

    :param analysis_id: Belong to analysis
    :param src_id: An upstream dependent AnalysisStepElementModel.src_id
    :param output_name: Be dependent on Task An output of
    :return:
        There are two types of output：
        - Entity data（file/file）/In-memory data： Dict
        - Others： value
    """
    # Flag is operating correctly
    _code = status.HTTP_200_OK
    msg = "success"
    data = None

    # Judgment Be dependent on Does it exist
    analysisStepElementModel = AnalysisStepElementModel.objects(
        analysis=analysis_id,
        src_id=src_id
    ).first()
    if not analysisStepElementModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"analysisStepElementModel not found for: {analysis_id}"
        return _code, msg, data
    # JudgmentTypes： TASK
    if analysisStepElementModel.type != "TASK":
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"analysisStepElementModel is not TASK, not have outputs: {analysisStepElementModel.type}"
        return _code, msg, data
    # Judgment: state
    if analysisStepElementModel.state.upper() != "SUCCESS":
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid analysisStepElementModel state: {analysisStepElementModel.state}"
        return _code, msg, data

    #
    outputs = analysisStepElementModel.outputs  # List[Dict]
    if not all([outputs, isinstance(outputs, List)]):
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid analysisStepElementModel outputs: {outputs}"
        return _code, msg, data

    #
    has_found = False
    for output in outputs:
        if not isinstance(output, Dict):
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"analysisStepElementModel has invalid output format: {output}"
            return _code, msg, data
        if output.get("name") == output_name:
            has_found = True
            data = output.get("data")
            break
    if has_found is False:
        _code = status.HTTP_404_NOT_FOUND
        msg = f"not found analysisStepElementModel.output with name `{output_name}`: {outputs}"
    return _code, msg, data


def get_data_for_task_element_inputs_from_dependent_element_outputs(
        analysis_id: str,
        element_id: str,
        with_do_update: bool = False
) -> Tuple[int, str, Any]:
    """
    :param analysis_id:
    :param element_id:
    :param with_do_update:
    :return:
    """

    # Flag is operating correctly
    _code = status.HTTP_200_OK
    msg = "success"
    data = None

    # JudgmentDoes it exist
    elementModel = AnalysisStepElementModel.objects(
        id=element_id
    ).first()
    if not elementModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"analysisStepElementModel not found for: {analysis_id}"
        return _code, msg, data

    # JudgmentTypes: It has to be TASK Types
    if elementModel.type != 'TASK':
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"analysisStepElementModel is not TASK type"
        return _code, msg, data

    # reading inputs
    inputs = elementModel.inputs
    if isinstance(inputs, List):
        # I iterate over each of them input
        for _input in inputs:
            if isinstance(_input, Dict) and bool(_input) is True:
                default_data_mode = _input.get("default_data_mode")
                # right input There are dependencies
                if default_data_mode == 'DEPENDENCY':
                    depend_on = _input.get("depend_on")
                    if isinstance(depend_on, Dict) and bool(depend_on) is True:
                        dependent_task_id = depend_on.get("task_id")
                        dependent_output_name = depend_on.get("output_name")
                        if all([dependent_task_id, dependent_output_name]):
                            dependent_src_id = dependent_task_id

                            # JudgmentBe dependent on： Does it exist
                            dependent_element_Model = AnalysisStepElementModel.objects(
                                analysis=analysis_id,
                                src_id=dependent_src_id
                            ).first()

                            if not dependent_element_Model:
                                _code = status.HTTP_400_BAD_REQUEST
                                msg = f"dependent element `{dependent_src_id}` not found for element `{element_id}`"
                                return _code, msg, data

                            if dependent_element_Model.type != "TASK":
                                _code = status.HTTP_400_BAD_REQUEST
                                msg = f"dependent element `{dependent_src_id}` is not TASK type, invalid"
                                return _code, msg, data

                            # outputs
                            outputs = dependent_element_Model.outputs
                            if (not outputs) or (not isinstance(outputs, List)):
                                _code = status.HTTP_400_BAD_REQUEST
                                msg = f"dependent element `{dependent_src_id}` has invalid outputs: {outputs}"
                                return _code, msg, data

                            # identifier
                            has_found = False
                            for output in outputs:
                                if output.get("name") == dependent_output_name:
                                    data = output.get("data")
                                    has_found = True
                                    break
                            if has_found is False:
                                _code = status.HTTP_404_NOT_FOUND
                                msg = f"not found dependent_element output `{dependent_output_name}`: {outputs}"
                            else:
                                # Whether to also update the current input parameters
                                if with_do_update is True:
                                    _input['data'] = data

    # Update or not inputs
    if isinstance(inputs, List) and with_do_update is True:
        elementModel.inputs = inputs
        elementModel.updated_at = datetime.utcnow()
        elementModel.save()
        elementModel.reload()
    #
    return _code, msg, data


def get_data_for_non_task_element_from_dependent_element_output(
        analysis_id: str,
        element_id: str,
        with_do_update: bool = False
) -> Tuple[int, str, Any]:
    """
    :param analysis_id:
    :param element_id:
    :param with_do_update:
    :return:
    """

    # Flag is operating correctly
    _code = status.HTTP_200_OK
    msg = "success"
    data = None

    # JudgmentDoes it exist
    elementModel = AnalysisStepElementModel.objects(
        id=element_id
    ).first()
    if not elementModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"analysisStepElementModel not found for: {analysis_id}"
        return _code, msg, data

    # JudgmentTypes: Not allowed yes TASK Types
    if elementModel.type == 'TASK':
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"analysisStepElementModel is TASK type"
        return _code, msg, data

    # derived_from_src_id
    # derived_from_output_name
    derived_from_src_id = elementModel.derived_from_src_id
    derived_from_output_name = elementModel.derived_from_output_name

    if not all([derived_from_src_id, derived_from_output_name]):
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"analysisStepElementModel has invalid derived_from_src_id `{derived_from_src_id}` or derived_from_output_name `{derived_from_output_name}`"
        return _code, msg, data

    # JudgmentBe dependent on： Does it exist
    dependent_element_Model = AnalysisStepElementModel.objects(
        analysis=analysis_id,
        src_id=derived_from_src_id
    ).first()

    if not dependent_element_Model:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"dependent element `{derived_from_src_id}` not found for element `{element_id}`"
        return _code, msg, data

    if dependent_element_Model.type != "TASK":
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"dependent element `{derived_from_src_id}` is not TASK type, invalid"
        return _code, msg, data

    # outputs
    outputs = dependent_element_Model.outputs
    if (not outputs) or (not isinstance(outputs, List)):
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"dependent element `{derived_from_src_id}` has invalid outputs: {outputs}"
        return _code, msg, data

    # identifier
    has_found = False
    for output in outputs:
        if output.get("name") == derived_from_output_name:
            data = output.get("data")
            has_found = True
            break
    if has_found is False:
        _code = status.HTTP_404_NOT_FOUND
        msg = f"not found dependent_element output `{derived_from_output_name}`: {outputs}"
    else:
        # Update at the same time?
        if with_do_update is True:
            elementModel.data = data
            elementModel.updated_at = datetime.utcnow()
            elementModel.save()
            elementModel.reload()
    #
    return _code, msg, data


