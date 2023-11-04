from typing import Union, Dict
from decimal import Decimal
from mongoengine.queryset.visitor import Q

from app.models.mongo import (
    AnalysisModel2,
    UserModel,
    UserQuotaStatementModel,
)
from app.usecases.quota_usecase import read_event_quota_used
from app.utils.common import convert_mongo_document_to_data


def read_analysis(
        analysis_id: str
) -> Dict:
    """

    :param analysis_id:
    :return:
    """

    #
    analysisModel = AnalysisModel2.objects(id=analysis_id).first()
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

    #
    return analysis_data


def read_analyses(
        is_trial: Union[bool, None] = None,
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

    :param is_trial:
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

    if is_trial is True:
        query = Q(is_trial=True)
    else:
        query = Q(is_trial__ne=True)
        # Determine whether to view only yourself
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
    count_all = AnalysisModel2.objects(query).count()
    count_completed = AnalysisModel2.objects(query & Q(state="COMPLETED")).count()
    count_incompleted = AnalysisModel2.objects(query & Q(state="INCOMPLETED")).count()

    # Analyzing the state
    if state:
        query = query & Q(state=state)

    total = AnalysisModel2.objects(query).count()
    # Sorting
    if sort == 'desc':
        analysisModels = AnalysisModel2.objects(query).order_by("-created_at")[skip: skip + size]
    else:
        analysisModels = AnalysisModel2.objects(query).order_by("created_at")[skip: skip + size]

    data = []
    for analysisModel in analysisModels:
        analysis_data = read_analysis(
            analysis_id=analysisModel.id
        )
        analysis_data['quota'] = read_event_quota_used(analysisModel)
        data.append(analysis_data)

    content = {
        "count_all": count_all,
        "count_completed": count_completed,
        "count_incompleted": count_incompleted,
        "total": total,
        "data": data
    }
    return content
