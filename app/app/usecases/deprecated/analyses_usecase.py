from typing import Union, Dict, List, Optional

from fastapi import Depends, status
from fastapi.encoders import jsonable_encoder
from mongoengine import Document
from mongoengine.queryset.visitor import Q
from starlette.responses import JSONResponse

from app.api import deps
from app.models.mongo import UserModel
from app.models.mongo.deprecated import (
    AnalysisModel,
    AnalysisStepElementModel,
    AnalysisStepModel,
)
from app.utils.common import convert_mongo_document_to_data


def read_analysis(
        analysis_id: str,
        with_steps_data: bool = False,
        with_steps_states: bool = False,
        with_elements_data: bool = False
) -> Dict:
    """

    :param analysis_id:
    :param with_steps_data:
    :param with_steps_states:   Must have with_steps_data = True when，It works
    :param with_elements_data:
    :return:
    """

    #
    analysisModel = AnalysisModel.objects(id=analysis_id).first()
    if not analysisModel:
        return {}

    # Initialization： analysis_data
    analysis_data = convert_mongo_document_to_data(analysisModel)

    # Tool name
    try:
        analysis_data['skeleton_name'] = analysisModel.skeleton.name
    except Exception as e:
        analysis_data['skeleton_name'] = ""

    # Author Information
    try:
        analysis_data["creator"] = analysisModel.user.name
    except Exception as e:
        print(f"user_id: {analysis_data['user']}")
        print(f"invalid analysis: {analysisModel.id}")
        analysis_data["creator"] = ""

    # Judgment：Do you carry it? steps data
    if with_steps_data is True:
        # analysis.steps
        step_data_list = []
        step_ids = analysisModel.steps  # List[str]
        if isinstance(step_ids, List):
            for step_id in step_ids:
                analysisStepModel = AnalysisStepModel.objects(id=step_id).first()
                if not analysisStepModel:
                    continue
                step_data = convert_mongo_document_to_data(analysisStepModel)

                # Judgment：Do you carry it? elements data
                if with_elements_data is True:
                    # analysis.step.elements
                    element_data_list = []
                    element_ids = analysisStepModel.elements
                    if isinstance(element_ids, List):
                        for element_id in element_ids:
                            elementModel = AnalysisStepElementModel.objects(id=element_id).first()
                            if not elementModel:
                                continue
                            element_data_list.append(convert_mongo_document_to_data(elementModel))
                    # elements
                    step_data["elements"] = element_data_list

                step_data_list.append(step_data)
        # substitution steps
        analysis_data["steps"] = step_data_list

        # JudgmentDo you carry it? state
        if with_steps_states:
            # steps states
            steps_states = [data.get("state") for data in step_data_list]
            analysis_data['steps_states'] = steps_states
    #
    return analysis_data


def read_analyses(
        name: Union[str, None] = None,
        creator: Union[str, None] = None,
        skeleton_id: Union[str, None] = None,
        state: Union[str, None] = None,
        page: int = 0,
        size: int = 10,
        viewer: UserModel = None,
        only_own: bool = True,
        sort: str = 'desc'
) -> Dict:
    """

    :param name:
    :param creator:
    :param skeleton_id:
    :param state:
    :param page:
    :param size:
    :param viewer:
    :param only_own: Users only view their own list of analyses， The background management configures the user to view all the analysis lists
    :param sort:
    :return:
    """

    skip = page * size

    query = Q(is_trial__ne=True)
    # Judgment
    if only_own is True and viewer is not None:
        query = query & Q(user=viewer.id)
    # Name of experiment
    if name:
        query = query & Q(name__icontains=name)
    # Name of author
    if creator:
        creators = UserModel.objects(name__icontains=creator).all()
        if creators:
            user_ids = [creator.id for creator in creators]
            query = query & Q(user__in=user_ids)
    # Tools id
    if skeleton_id:
        query = query & Q(skeleton=skeleton_id)

    # counts： Because state Participate in retrieval，So counting all kinds of things counts Must be placed in `state` Before
    count_all = AnalysisModel.objects(query).count()
    count_completed = AnalysisModel.objects(query & Q(state="COMPLETED")).count()
    count_incompleted = AnalysisModel.objects(query & Q(state="INCOMPLETED")).count()

    # Analyzing the state
    if state:
        query = query & Q(state=state)

    total = AnalysisModel.objects(query).count()
    # Sorting
    if sort == 'desc':
        analysisModels = AnalysisModel.objects(query).order_by("-created_at")[skip: skip + size]
    else:
        analysisModels = AnalysisModel.objects(query).order_by("created_at")[skip: skip + size]

    data = []
    for analysisModel in analysisModels:
        analysis_data = read_analysis(
            analysis_id=analysisModel.id,
            with_steps_data=True,
            with_steps_states=True,
            with_elements_data=False
        )
        #
        data.append(analysis_data)
    content = {
        "count_all": count_all,
        "count_completed": count_completed,
        "count_incompleted": count_incompleted,
        "total": total,
        "data": data
    }
    return content
