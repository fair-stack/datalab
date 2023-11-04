import copy
from functools import lru_cache
from typing import Optional, Dict, List, Tuple

from fastapi import status

from app.models.mongo.deprecated import (
    CompoundStepElementModel,
    CompoundStepModel,
    SkeletonModel,
)
from app.utils.common import convert_mongo_document_to_data

"""
note：In the following task and data Both refer to the construction based on this CompoundStepElement
"""


@lru_cache(maxsize=1)
def get_skeleton_experiment_tasks(skeleton_id: str) -> Optional[List[Dict]]:
    resp = None
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if skeletonModel:
        resp = skeletonModel.experiment_tasks
    return resp


@lru_cache(maxsize=1)
def get_skeleton_experiment_task(skeleton_id: str, task_id: str) -> Optional[Dict]:
    resp = None
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if skeletonModel:
        data_list = skeletonModel.experiment_tasks
        for data in data_list:
            if data.get("task_id") == task_id:
                resp = copy.deepcopy(data)
                break
    return resp


@lru_cache(maxsize=1)
def get_skeleton_experiment_datasets(skeleton_id: str) -> Optional[List[Dict]]:
    resp = None
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if skeletonModel:
        resp = skeletonModel.experiment_tasks_datasets
    return resp


@lru_cache(maxsize=1)
def get_skeleton_experiment_dataset(skeleton_id: str, dataset_id: str) -> Optional[Dict]:
    resp = None
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if skeletonModel:
        data_list = skeletonModel.experiment_tasks_datasets
        for data in data_list:
            # Use the DataFileSystem， Use the id，No _id
            data_id = data.get("id")
            if data_id == dataset_id:
                resp = copy.deepcopy(data)
                break
    return resp


def check_data_has_conjugated_task_in_same_compoundstep(
        skeleton_id: str,
        compoundstep_id: str,
        src_id: str,
        derived_from_src_id: str) -> Tuple[int, str, Optional[bool]]:
    """
    check Data (Corresponding to Element Not created yet) Whether and origin Task (Corresponding to Element Created) Appearing in a CompoundStep

    :return: bool:
        - True, Coexistence
        - False， Coexistence
    """
    _code = status.HTTP_200_OK
    is_coexist = None

    dataset_data = get_skeleton_experiment_dataset(
        skeleton_id=skeleton_id,
        dataset_id=src_id
    )
    if not dataset_data:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton experiment_dataset not found: <skeleton_id> - <src_id>: [{skeleton_id}]: [{src_id}]"
        return _code, msg, is_coexist

    if not compoundstep_id:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid compoundstep_id: {compoundstep_id}"
        return _code, msg, is_coexist

    compoundStepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not compoundStepModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"CompoundStep not found for: {compoundstep_id}"
        return _code, msg, is_coexist

    # elements
    current_elements = compoundStepModel.elements
    if not current_elements:
        current_elements = []

    for e_id in current_elements:  # List[str]
        element = CompoundStepElementModel.objects(id=e_id).first()
        if not element:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStepElement not found for: {e_id}"
            return _code, msg, is_coexist
        # Target type： Task
        if (element.type == 'TASK') and (element.src_id == derived_from_src_id):
            # msg = f"current Data's conjugated Task coexist in same CompoundStep"
            msg = f"same CompoundStep In the，Current experimental output data exist [{dataset_data.get('name')}] Corresponding toExperimental Procedures [{element.name}]，Not allowedCoexistence"
            is_coexist = True
            return _code, msg, is_coexist
    # msg = f"current Data's conjugated Task NOT coexist in same CompoundStep"
    msg = f"same CompoundStep In the，Current experimental output data exist [{dataset_data.get('name')}] Corresponding toExperimental Procedures"
    is_coexist = False
    return _code, msg, is_coexist


def check_data_has_conjugated_task_in_upstream_compoundsteps(
        skeleton_id: str,
        current_compoundstep_id: str,
        src_id: str,
        derived_from_src_id: str
) -> Tuple[int, str, Optional[bool]]:
    """
    Judgment Data (Corresponding to Element Not created yet)upstreamexistenceCorresponding to Task (Corresponding to Element Created)（across CompoundStep）

    :param skeleton_id:
    :param current_compoundstep_id:  Data Be located in CompoundStep
    :param src_id:
    :param derived_from_src_id: produce Data the task the src_id
    :return:

    """
    # _code: Flag is operating correctly
    _code = status.HTTP_200_OK
    has_conjugated = None

    dataset_data = get_skeleton_experiment_dataset(
        skeleton_id=skeleton_id,
        dataset_id=src_id
    )
    if not dataset_data:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton experiment_dataset not found: <skeleton_id> - <src_id>: [{skeleton_id}]: [{src_id}]"
        return _code, msg, has_conjugated

    if not skeleton_id:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid skeleton_id: {skeleton_id}"
        return _code, msg, has_conjugated

    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton not found for: {skeleton_id}"
        return _code, msg, has_conjugated

    # compoundsteps_ids Range of interception：0-Current(Free of)
    steps_ids = skeletonModel.compoundsteps
    if (not steps_ids) or (not isinstance(steps_ids, List)):
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"compoundsteps not found for Skeleton: {skeleton_id}"
        return _code, msg, has_conjugated

    if current_compoundstep_id not in steps_ids:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"current_compoundstep_id `{current_compoundstep_id}` not found in Skeleton.compoundsteps `{steps_ids}`"
        return _code, msg, has_conjugated
    # upstreamthe steps（Free of）
    upstream_steps_ids = steps_ids[:steps_ids.index(current_compoundstep_id)]
    # getupstreamthe elements，And filter it TASK Types
    upstream_steps_elements = []
    for step_id in upstream_steps_ids:
        stepModel = CompoundStepModel.objects(id=step_id).first()
        if not stepModel:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"Upstream CompoundStep not found: {step_id}"
            return _code, msg, has_conjugated
        _elements = stepModel.elements  # List[str]
        if isinstance(_elements, List):
            upstream_steps_elements.extend(_elements)
    # Filtering, Types： TASK
    for element_id in upstream_steps_elements:
        upstream_element = CompoundStepElementModel.objects(id=element_id).first()
        if not upstream_element:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"Upstream CompoundStepElement not found: {element_id}"
            return _code, msg, has_conjugated
        upstream_element_src_id = upstream_element.src_id
        # Find out
        if upstream_element_src_id == derived_from_src_id:
            # msg = f"relevant task found in Upstream CompoundSteps for data: {data_derived_from_src_id}"
            msg = f"upstreamthe CompoundSteps In the，existenceCurrent [{dataset_data.get('name')}] theExperimental Procedures [{upstream_element.name}]"
            has_conjugated = True
            return _code, msg, has_conjugated
    # Find out
    _code = status.HTTP_200_OK
    # msg = f"no relevant task found in Upstream CompoundSteps for data: {data_derived_from_src_id}"
    msg = f"upstreamthe CompoundStep In the，existenceCurrent [{dataset_data.get('name')}] theExperimental Procedures"
    has_conjugated = False
    return _code, msg, has_conjugated


def check_duplicated_task_in_compoundstep(compoundstep_id: str, src_id: str):
    """

    :return:
    """
    # _code: Flag is operating correctly
    duplicated = None
    _code = status.HTTP_200_OK

    if not compoundstep_id:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid compoundstep_id: {compoundstep_id}"
        return _code, msg, duplicated

    stepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not stepModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"CompoundStep not found for: {compoundstep_id}"
        return _code, msg, duplicated
    skeleton_elements = stepModel.elements  # List[str]
    for e_id in skeleton_elements:
        element = CompoundStepElementModel.objects(id=e_id).first()
        if not element:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStepElement not found for: {e_id}"
            return _code, msg, duplicated
        if element.type == 'TASK' and element.src_id == src_id:
            msg = f"duplicated usage of Task in one CompoundStep is forbidden: {src_id}"
            msg = f"same CompoundStep In the，existenceUse thesameExperimental Procedures，Not allowed"
            duplicated = True
            return _code, msg, duplicated

    msg = f"same CompoundStep In the，existenceUse thesameExperimental Procedures"
    duplicated = False
    return _code, msg, duplicated


def check_duplicated_data_in_compoundstep(compoundstep_id: str, src_id: str):
    """

    :return:
    """
    _code = status.HTTP_200_OK
    duplicated = None

    if not compoundstep_id:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid compoundstep_id: {compoundstep_id}"
        return _code, msg, duplicated

    stepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not stepModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"CompoundStep not found for: {compoundstep_id}"
        return _code, msg, duplicated
    skeleton_elements = stepModel.elements  # List[str]
    for e_id in skeleton_elements:
        element = CompoundStepElementModel.objects(id=e_id).first()
        if not element:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStepElement not found for: {e_id}"
            return _code, msg, duplicated
        if element.type != 'TASK' and element.src_id == src_id:
            # msg = f"duplicated usage of Data in one CompoundStep is forbidden: {src_id}"
            msg = f"same CompoundStep In the，existenceUse thesame，Not allowed"
            duplicated = True
            return _code, msg, duplicated
    # msg = "no duplicated usage of Data in one CompoundStep"
    msg = f"same CompoundStep In the，existenceUse thesame"
    duplicated = False
    return _code, msg, duplicated


def check_duplicated_task_in_skeleton(skeleton_id: str, src_id: str):
    """

    :return:
    """
    _code = status.HTTP_200_OK
    duplicated = None

    if not skeleton_id:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid skeleton_id: {skeleton_id}"
        return _code, msg, duplicated

    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton not found for: {skeleton_id}"
        return _code, msg, duplicated

    skeleton_elements = []  # List[str]
    compoundsteps = skeletonModel.compoundsteps  # List[str]
    for step_id in compoundsteps:
        stepModel = CompoundStepModel.objects(id=step_id).first()
        if not stepModel:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStep not found for: {step_id}"
            return _code, msg, duplicated
        eles = stepModel.elements  # List[str]
        if isinstance(eles, List):
            skeleton_elements.extend(eles)
    for e_id in skeleton_elements:
        element = CompoundStepElementModel.objects(id=e_id).first()
        if not element:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStepElement not found for: {e_id}"
            return _code, msg, duplicated
        if element.type == 'TASK' and element.src_id == src_id:
            # msg = f"duplicated usage of Task in one Skeleton is forbidden: {src_id}"
            msg = f"sameIn the，existenceUse thesameExperimental Procedures，Not allowed"
            duplicated = True
            return _code, msg, duplicated
    # msg = "no duplicated usage of Task in one Skeleton"
    msg = f"sameIn the，existenceUse thesameExperimental Procedures"
    duplicated = False
    return _code, msg, duplicated


def check_task_has_conjugated_data_in_same_compoundstep(
        skeleton_id: str,
        compoundstep_id: str,
        src_id: str) -> Tuple[int, str, Optional[bool]]:
    """
    check Task (Corresponding to Element Not created yet) Corresponding to Data（Corresponding to Element Created） Appearing in a CompoundStep

    :return: bool:
        - True, Coexistence
        - False， Coexistence
    """
    _code = status.HTTP_200_OK
    is_coexist = None

    # Use thethe task existence
    task_data = get_skeleton_experiment_task(skeleton_id=skeleton_id, task_id=src_id)
    if not task_data:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton experiment_task not found for: <skeleton_id> - <task_id>: {skeleton_id} : {src_id}"
        return _code, msg, is_coexist

    if not compoundstep_id:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid compoundstep_id: {compoundstep_id}"
        return _code, msg, is_coexist

    compoundStepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not compoundStepModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"CompoundStep not found for: {compoundstep_id}"
        return _code, msg, is_coexist

    # elements
    current_elements = compoundStepModel.elements
    if not current_elements:
        current_elements = []

    for e_id in current_elements:  # List[str]
        element = CompoundStepElementModel.objects(id=e_id).first()
        if not element:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStepElement not found for: {e_id}"
            return _code, msg, is_coexist
        # Target type： Data
        if (element.type != 'TASK') and (element.derived_from_src_id == src_id):
            # msg = f"current Task's conjugated Data coexist in same CompoundStep"
            msg = f"same CompoundStep In the，existenceCurrentExperimental Procedures [{task_data.get('task_name')}] Corresponding to [{element.name}]，Not allowedCoexistence"
            is_coexist = True
            return _code, msg, is_coexist
    # msg = f"current Task's conjugated Data NOT coexist in same CompoundStep"
    msg = f"same CompoundStep In the，existenceCurrentExperimental Procedures [{task_data.get('task_name')}] Corresponding to"
    is_coexist = False
    return _code, msg, is_coexist


def check_task_has_conjugated_data_in_skeleton_upstream_compoundsteps(
        skeleton_id: str,
        compoundstep_id: str,
        src_id: str
) -> Tuple[int, str, Optional[bool]]:
    """
    - this Task (Corresponding to Element Not created yet) Corresponding to Data （Corresponding to Element Created） inthis Task Above （Current CompoundStep the（Free of））： Iterate over all upstream elements， Judgmentexistence data（derived_from_src_id）:
        - YES: Not allowed，Back to Tips
        - NO: continue

    :param skeleton_id:
    :param compoundstep_id:
    :param src_id:
    :return:
    """

    _code = status.HTTP_200_OK
    has_conjugate = None

    # Use thethe task existence
    task_data = get_skeleton_experiment_task(skeleton_id=skeleton_id, task_id=src_id)
    if not task_data:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton experiment_task not found for: <skeleton_id> - <task_id>: {skeleton_id} : {src_id}"
        return _code, msg, has_conjugate

    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton not found for: {skeleton_id}"
        return _code, msg, has_conjugate

    # Judgmentthe compoundstep_id
    compoundsteps = skeletonModel.compoundsteps  # List[str]
    if compoundstep_id not in compoundsteps:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f" {compoundstep_id} not found in Skeleton.compoundsteps"
        return _code, msg, has_conjugate
    # upstreamthe compoundsteps，Free of
    current_compoundstep_index = compoundsteps.index(compoundstep_id)
    upstream_compoundsteps = compoundsteps[:current_compoundstep_index]
    # getCorresponding to elements
    upstream_compoudsteps_elements = []
    for step_id in upstream_compoundsteps:
        stepModel = CompoundStepModel.objects(id=step_id).first()
        if not stepModel:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStep not found for: {step_id}"
            return _code, msg, has_conjugate
        eles = stepModel.elements  # List[str]
        if isinstance(eles, List):
            upstream_compoudsteps_elements.extend(eles)
    for e_id in upstream_compoudsteps_elements:
        element = CompoundStepElementModel.objects(id=e_id).first()
        if not element:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStepElement not found for: {e_id}"
            return _code, msg, has_conjugate
        # Target type： Data
        if element.type != 'TASK' and element.derived_from_src_id == src_id:
            # msg = f"conjugated data found in skeleton upstream compoundsteps for task"
            msg = f"upstreamthe CompoundSteps Within the，existenceCurrentExperimental Procedures [{task_data.get('task_name')}] Corresponding to [{element.name}]，Not allowed"
            has_conjugate = True
            return _code, msg, has_conjugate
    # msg = f"no conjugated data found in skeleton upstream compoundsteps for task"
    msg = f"upstreamthe CompoundSteps Within the，existenceCurrentExperimental Procedures [{task_data.get('task_name')}] Corresponding to"
    has_conjugate = False
    return _code, msg, has_conjugate


def check_task_inputs_and_outputs_dependencies_well_maintained_in_skeleton(
        skeleton_id: str,
        compoundstep_id: str,
        loc_index: int,
        task_id: str
) -> Tuple[int, str, Optional[bool]]:
    """
    - Based on element Information，Judgmentthe tasks_dependencies （Through the `SkeletonModel.experiment_tasks_dependencies` get）
      - Input dependencies:    the element Not in the moment element Below
      - The output is dependent on:  thisthe element Not in the moment element Above
      - Whether dependencies are broken：
          - YES： Not allowed，Back to Tips
          - NO： continue

    :param skeleton_id:
    :param compoundstep_id:
    :param loc_index:  src_id in compoundstep Within thethe
    :param task_id:
    :return:
    """
    _code = status.HTTP_200_OK
    is_dependency_broken = None

    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"Skeleton not found for: {skeleton_id}"
        return _code, msg, is_dependency_broken

    compoundStepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not compoundStepModel:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"CompoundStep not found for: {compoundstep_id}"
        return _code, msg, is_dependency_broken

    # preset
    compoundsteps = skeletonModel.compoundsteps  # List[str]

    # get：Used for subsequent
    # experiment_tasks_dependencies
    experiment_tasks_dependencies = skeletonModel.experiment_tasks_dependencies
    # elements
    current_elements = compoundStepModel.elements
    if not current_elements:
        current_elements = []

    # upstream
    # note： upstream_compoudsteps_elements （Current compoundstep） Be different from upstream_elements （Current compoundstep，Current）
    upstream_elements = []
    current_compoundstep_index = compoundsteps.index(compoundstep_id)
    upstream_compoundsteps = compoundsteps[:current_compoundstep_index]
    for step_id in upstream_compoundsteps:
        stepModel = CompoundStepModel.objects(id=step_id).first()
        if not stepModel:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"CompoundStep not found for: {step_id}"
            return _code, msg, is_dependency_broken
        eles = stepModel.elements  # List[str]
        if isinstance(eles, List):
            upstream_elements.extend(eles)

    # PlusCurrent CompoundStep Within theCurrentthe
    if loc_index == -1:
        current_compoundstep_current_element_upstream_elements = copy.deepcopy(current_elements)
        current_compoundstep_current_element_downstream_elements = []
    else:
        current_compoundstep_current_element_upstream_elements = copy.deepcopy(current_elements[:loc_index])
        current_compoundstep_current_element_downstream_elements = copy.deepcopy(
            current_elements[loc_index + 1:])
    # Plus
    upstream_elements.extend(current_compoundstep_current_element_upstream_elements)

    # downstream
    downstream_elements = []
    downstream_compoundsteps = compoundsteps[(current_compoundstep_index + 1):]
    for step_id in downstream_compoundsteps:
        stepModel = CompoundStepModel.objects(id=step_id).first()
        eles = stepModel.elements  # List[str]
        if isinstance(eles, List):
            downstream_elements.extend(eles)
    # Plus
    downstream_elements.extend(current_compoundstep_current_element_downstream_elements)

    # get dependency
    element_dependencies = None  # Optional[Dict]
    for d in experiment_tasks_dependencies:
        if task_id == d.get("task_id"):
            element_dependencies = copy.deepcopy(d)
            break

    print(f"element_dependencies: {element_dependencies}")
    #
    if not element_dependencies:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"element dependency not found for {task_id}"
        return _code, msg, is_dependency_broken

    #
    if not isinstance(element_dependencies, Dict):
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid dependencies for element: {task_id}"
        return _code, msg, is_dependency_broken
    # name
    task_name = element_dependencies.get("task_name")
    if not task_name:
        _code = status.HTTP_400_BAD_REQUEST
        msg = f"element source task_name not found for {task_id}"
        return _code, msg, is_dependency_broken

    #
    inputs = element_dependencies.get("inputs", [])
    # Judgmentdownstream Current element theInput dependenciesthe element
    for _input in inputs:
        print(f"_input: {_input}")
        input_name = _input.get("name")
        if not input_name:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"invalid input_name `{input_name}`"
            return _code, msg, is_dependency_broken
        input_depend_on = _input.get("depend_on")
        # depend_on Judgment： If is {}， Then ignore
        if isinstance(input_depend_on, Dict):
            # Judgment {}
            if input_depend_on is {}:
                continue
            #
            input_depend_on_task_id = input_depend_on.get("task_id")
            input_depend_on_task_name = input_depend_on.get("task_name")
            input_depend_on_task_output_name = input_depend_on.get("output_name")
            #
            for downstream_element_id in downstream_elements:
                downstream_element = CompoundStepElementModel.objects(id=downstream_element_id).first()
                if not downstream_element:
                    _code = status.HTTP_400_BAD_REQUEST
                    msg = f"downstream_element [{downstream_element_id}] not found for element: {task_id}"
                    return _code, msg, is_dependency_broken
                downstream_element_src_id = downstream_element.src_id
                # comparison
                if input_depend_on_task_id == downstream_element_src_id:
                    # msg = f"invalid order: {task_name}.inputs.{input_name} should depend on {input_depend_on_task_name}.outputs.{input_depend_on_task_output_name}"
                    msg = f"It is forbidden to break the dependency order: Experimental Procedures [{task_name}] the [{input_name}] Experimental Procedures [{input_depend_on_task_name}] the [{input_depend_on_task_output_name}]"
                    is_dependency_broken = True
                    return _code, msg, is_dependency_broken
        else:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"invalid input_depend_on `{input_depend_on}` for input: {input_name}"
            return _code, msg, is_dependency_broken

    outputs = element_dependencies.get("outputs", [])
    # Judgmentupstream Current element thethe element
    for output in outputs:
        output_name = output.get("name")
        if not output_name:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"invalid output_name `{output_name}`"
            return _code, msg, is_dependency_broken
        output_depended_by_list = output.get("depended_by", [])  # List[Dict]
        if isinstance(output_depended_by_list, List):
            for output_depended_by in output_depended_by_list:
                output_depended_by_task_id = output_depended_by.get("task_id")
                output_depended_by_task_name = output_depended_by.get("task_name")
                output_depended_by_task_input_name = output_depended_by.get("input_name")
                #
                for upstream_element_id in upstream_elements:
                    upstream_element = CompoundStepElementModel.objects(id=upstream_element_id).first()
                    if not upstream_element:
                        _code = status.HTTP_400_BAD_REQUEST
                        msg = f"upstream_element [{upstream_element_id}] not found for element: {task_id}"
                        return _code, msg, is_dependency_broken
                    upstream_element_src_id = upstream_element.src_id
                    # comparison
                    if output_depended_by_task_id == upstream_element_src_id:
                        # msg = f"invalid order: {task_name}.outputs.{output_name} should be depended by {output_depended_by_task_name}.inputs.{output_depended_by_task_input_name}"
                        msg = f"It is forbidden to break the dependency order: Experimental Procedures [{task_name}] the [{output_name}] Experimental Procedures [{output_depended_by_task_name}] the [{output_depended_by_task_input_name}] Rely on"
                        is_dependency_broken = True
                        return _code, msg, is_dependency_broken
        else:
            _code = status.HTTP_400_BAD_REQUEST
            msg = f"invalid depended_by `{output_depended_by_list}` for output_name `{output_name}`"
            return _code, msg, is_dependency_broken

    msg = "dependencies well maintained"
    is_dependency_broken = False
    return _code, msg, is_dependency_broken


def read_compoundstep(compoundstep_id: str) -> Tuple[int, str, Optional[Dict]]:
    """

    :param compoundstep_id:
    :return:
    """
    code = status.HTTP_200_OK
    msg = "success"
    compoundstep_data = None

    compoundStepModel = CompoundStepModel.objects(id=compoundstep_id).first()
    if not compoundStepModel:
        code = status.HTTP_404_NOT_FOUND
        msg = f"CompoundStepModel not found: {compoundstep_id}"
        return code, msg, compoundstep_data

    # elements_data
    elements_data = []
    elements = compoundStepModel.elements  # List[str]
    if isinstance(elements, List):
        for element_id in elements:
            # Judgment Element
            elementModel = CompoundStepElementModel.objects(id=element_id).first()
            if not elementModel:
                code = status.HTTP_404_NOT_FOUND
                msg = f"CompoundStepElementModel not found: {element_id}"
                return code, msg, compoundstep_data

            # element_data
            element_data = convert_mongo_document_to_data(elementModel)
            elements_data.append(element_data)

    # step_data
    compoundstep_data = convert_mongo_document_to_data(compoundStepModel)
    compoundstep_data["elements"] = elements_data
    #
    return code, msg, compoundstep_data
