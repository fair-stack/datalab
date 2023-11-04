from typing import Optional, Dict, List

from fastapi import (
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.models.mongo import UserModel, PermissionModel
from app.utils.common import convert_mongo_document_to_data
from app.utils.constants import (
    PERMISSION_MAP,
    PERMISSION_TOPOLOGY,
)


def _iter_create_permission_model(data: Dict, parent_id: str = None) -> Optional[Dict]:
    code = data.get("code")
    name = data.get("name")
    is_group = PERMISSION_MAP.get(code, dict()).get("is_group", False)
    children = data.get("children", [])
    uri = PERMISSION_MAP.get(code, dict()).get("uri")
    # verification
    if code not in PERMISSION_MAP.keys():
        return
    if name != PERMISSION_MAP.get(code).get("name"):
        return
    # Judgment
    permModel = PermissionModel.objects(id=code).first()
    if permModel is None:
        # Create
        permModel = PermissionModel(
            id=code,
            code=code,
            name=name,
            is_group=is_group,
            parent=parent_id if parent_id else None,
            children=[c.get("code") for c in children] if children else None,
            uri=uri
        )
        permModel.save()
        if children:
            for sub_perm in children:
                _iter_create_permission_model(sub_perm, parent_id=code)
    return convert_mongo_document_to_data(permModel)


def pre_check_permissions_exist():
    # Judgment
    total = PermissionModel.objects.count()
    if total == 0:
        for perm_dict in PERMISSION_TOPOLOGY:
            _iter_create_permission_model(perm_dict, parent_id=None)


def _iter_get_permission_data(_id: str, all_checked: Optional[bool] = None, **check_options) -> Optional[Dict]:
    # Judgment
    permModel = PermissionModel.objects(id=_id).first()
    if permModel is None:
        return None
    else:
        data = convert_mongo_document_to_data(permModel)
        data["checked"] = all_checked if all_checked is not None else PERMISSION_MAP.get(_id, dict()).get("checked", False)
        # Fine-tuning permissions
        if check_options != {}:
            check_opt = check_options.get(data.get("code"))
            if isinstance(check_opt, bool):
                data['checked'] = check_opt

        children = permModel.children
        children_new = []
        if children:
            for code in children:
                c_data = _iter_get_permission_data(_id=code, all_checked=all_checked, **check_options)
                if c_data:
                    children_new.append(c_data)
        data["children"] = children_new
        return data


def get_permissions_tree_data(all_checked: Optional[bool] = None, **check_options) -> List[Optional[Dict]]:
    """

    :param all_checked:
    :param check_options: Fine-tune whether some permissions are True， Examples {'L2-09': True, 'L3-15': False}
    :return:
    """
    pre_check_permissions_exist()

    resp = []
    for perm_dict in PERMISSION_TOPOLOGY:
        code = perm_dict.get("code")
        permModel = PermissionModel.objects(id=code).first()
        data = convert_mongo_document_to_data(permModel)
        # Adding a field
        data["checked"] = all_checked if all_checked is not None else PERMISSION_MAP.get(code, dict()).get("checked", False)
        # Fine-tuning permissions
        if check_options != {}:
            check_opt = check_options.get(code)
            if isinstance(check_opt, bool):
                data['checked'] = check_opt

        children = data.get("children", [])
        children_new = []
        if children:
            for code in children:
                c_data = _iter_get_permission_data(_id=code, all_checked=all_checked, **check_options)
                if c_data:
                    children_new.append(c_data)
        data["children"] = children_new
        resp.append(data)
    return resp
