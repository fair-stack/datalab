from typing import Union, Dict, Tuple, Optional

from fastapi import Depends, status
from fastapi.encoders import jsonable_encoder
from mongoengine.queryset.visitor import Q
from starlette.responses import JSONResponse

from app.api import deps
from app.models.mongo import (
    ExperimentModel,
    ToolTaskModel,
    UserModel,
)
from app.utils.common import convert_mongo_document_to_data
from app.usecases.quota_usecase import read_event_quota_used


def read_experiments(
        is_shared: Union[bool, None] = None,
        name: Union[str, None] = None,
        creator: Union[str, None] = None,
        page: int = 0,
        size: int = 10,
        viewer: UserModel = None,
        only_own: bool = True,
        sort: str = 'desc'
) -> Dict:
    """

    :param is_shared:
    :param name:
    :param creator:
    :param page:
    :param size:
    :param viewer:
    :param only_own: Users only view their own list of experiments， The background management configures the user to view the list of all experiments
    :param sort: Default reverse order
    :return:
    """

    skip = page * size

    query = Q(is_trial__ne=True)
    # From sharing
    if is_shared is not None:
        if is_shared is True:
            query = query & Q(is_shared=True)
        else:
            query = query & Q(is_shared__ne=True)
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

    total = ExperimentModel.objects(query).count()

    # Sorting
    if sort == 'desc':
        expts = ExperimentModel.objects(query).order_by("-created_at")[skip: skip + size]
    else:
        expts = ExperimentModel.objects(query).order_by("created_at")[skip: skip + size]

    # serialization
    # Note：ExperimentModel Inside of user [ReferenceField]，Can't be used directly DatasetSchema Inside of user [str]
    data = []
    for expt in expts:
        _data = convert_mongo_document_to_data(expt)
        # get tasks quantity
        _data["tasks_count"] = 0 if bool(_data.get("tasks")) is False else len(_data.get("tasks"))
        # Author Information
        try:
            _data["creator"] = expt.user.name
        except Exception as e:
            print(f"user_id: {_data['user']}")
            print(f"invalid expt: {expt.id}")
            _data["creator"] = ""
        _data['quota'] = read_event_quota_used(expt)
        data.append(_data)
    content = {"msg": "success",
               "total": total,
               "data": data}
    return content


def check_if_shared_experiment(
        pk: str,
        pk_type: str = 'Experiment',
        ) -> Tuple[int, str, Optional[bool]]:
    """
    Determine if an uneditable experiment is being shared

        pk_type:
            - Experiment
            - Task

    :return:
    """
    code = status.HTTP_200_OK
    msg = None
    shared = None

    if pk_type == 'Experiment':
        exptModel = ExperimentModel.objects(id=pk).first()
        if not exptModel:
            code = status.HTTP_404_NOT_FOUND
            msg = f"experiment not found: {pk}"
        else:
            is_shared = exptModel.is_shared
            if is_shared is not None:
                if is_shared is True:
                    msg = "shared experiment"
                    shared = True
                else:
                    msg = "not shared experiment"
                    shared = False
    elif pk_type == 'Task':
        taskModel = ToolTaskModel.objects(id=pk).first()
        if not taskModel:
            code = status.HTTP_404_NOT_FOUND
            msg = f"experiment task not found: {pk}"
        else:
            try:
                exptModel = taskModel.experiment
                is_shared = exptModel.is_shared
                if is_shared is not None:
                    if is_shared is True:
                        msg = "shared experiment"
                        shared = True
                    else:
                        msg = "not shared experiment"
                        shared = False
            except Exception as e:
                print(e)
                code = status.HTTP_404_NOT_FOUND
                msg = f"experiment not found for task: {pk}"
    else:
        pass

    return code, msg, shared
