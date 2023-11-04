from collections import deque
from typing import Optional, Dict, List

from app.models.mongo import RoleModel, UserModel
from app.schemas import RoleBaseSchema
from app.usecases.permissions_usecase import get_permissions_tree_data
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.constants import ROLES_INNATE_MAP


def init_roles_innate():
    # ADMIN
    ROLE_ADMIN_MAP = ROLES_INNATE_MAP.get("ADMIN")
    r_admin_code = ROLE_ADMIN_MAP.get("code")
    r_admin_name = ROLE_ADMIN_MAP.get("name")
    r_admin = RoleModel.objects(name=r_admin_name).first()
    if not r_admin:
        print("innate role ADMIN not exists, creating")
        r_admin_perms = get_permissions_tree_data(all_checked=True)
        r_admin = RoleModel(
            id=r_admin_code,
            name=r_admin_name,
            permissions=r_admin_perms,
            is_innate=True
        )
        r_admin.save()

    # USER_SENIOR
    ROLE_USER_SENIOR_MAP = ROLES_INNATE_MAP.get("USER_SENIOR")
    r_user_senior_code = ROLE_USER_SENIOR_MAP.get("code")
    r_user_senior_name = ROLE_USER_SENIOR_MAP.get("name")
    r_user_senior = RoleModel.objects(name=r_user_senior_name).first()
    if not r_user_senior:
        print("innate role USER_SENIOR not exists, creating")
        r_user_senior_check_options = {
            "L1-01": True,  # Analysis tools
            "L1-02": True,  # Experiment
            "L2-01": True,  # Analysis tools
            "L2-02": True,  # Experiment
            "L2-03": True   # Publishing tools
        }
        r_user_senior_perms = get_permissions_tree_data(**r_user_senior_check_options)
        r_user_senior = RoleModel(
            id=r_user_senior_code,
            name=r_user_senior_name,
            permissions=r_user_senior_perms,
            is_innate=True
        )
        r_user_senior.save()

    # USER_NORMAL
    ROLE_USER_NORMAL_MAP = ROLES_INNATE_MAP.get("USER_NORMAL")
    r_user_normal_code = ROLE_USER_NORMAL_MAP.get("code")
    r_user_normal_name = ROLE_USER_NORMAL_MAP.get("name")
    r_user_normal = RoleModel.objects(name=r_user_normal_name).first()
    if not r_user_normal:
        print("innate role USER_NORMAL not exists, creating")
        r_user_normal_check_options = {
            "L1-01": True,  # Analysis tools
            "L1-02": True,  # Experiment
            "L2-01": True,  # Analysis tools
            "L2-02": False,  # Experiment
            "L2-03": False   # Publishing tools
        }
        r_user_normal_perms = get_permissions_tree_data(**r_user_normal_check_options)
        r_user_normal = RoleModel(
            id=r_user_normal_code,
            name=r_user_normal_name,
            permissions=r_user_normal_perms,
            is_innate=True
        )
        r_user_normal.save()


def read_roles() -> List[RoleBaseSchema]:
    """List of roles"""
    init_roles_innate()

    resp = []
    roles = RoleModel.objects.order_by("-created_at").all()
    for role in roles:
        schema = RoleBaseSchema(**convert_mongo_document_to_data(role))
        resp.append(schema)
    return resp


def admin_read_roles() -> List[Dict]:
    """List of roles"""
    init_roles_innate()

    resp = []
    roles = RoleModel.objects.order_by("-created_at").all()
    for role in roles:
        data = convert_mongo_document_to_data(role)
        # Get rid of permissions
        data.pop('permissions', None)
        # Number of users
        data['user_count'] = UserModel.objects(role=role.id).count()
        # Founder
        try:
            creator = UserModel.objects(id=role.creator).first()
            if creator:
                data["creator_name"] = creator.name
            else:
                data["creator_name"] = ''
        except Exception as e:
            data["creator_name"] = ''

        resp.append(data)
    return resp



def flatten_role_permissions(permissions: List[Dict]) -> Optional[List[Dict]]:
    """
    Flattening a role's tree permissions into a single one list
    """
    #  resp
    flat_permissions = []

    # Judgment
    if permissions in (None, [], [{}]):
        print(f'invalid permissions: {permissions}')
        return None

    # Strategy： Breadth first (After convenience request.url.path with permissions Comparison of)
    q = deque()
    q.extendleft(permissions)

    while q:
        perm = q.pop()
        tmp = {
            'id': perm.get("id"),
            'code': perm.get("code"),
            'name': perm.get("name"),
            'checked': perm.get("checked"),
            "uri": perm.get("uri")
        }
        flat_permissions.append(tmp)
        # Judgment children
        children = perm.get("children")
        if children not in (None, [], [{}]):
            q.extendleft(children)
    return flat_permissions
