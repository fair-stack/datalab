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
from app.models.mongo import RoleModel, UserModel
from app.schemas import (
    RoleBaseSchema,
    RoleCreateSchema,
    RoleSchema,
    RoleUpdateSchema,
)
from app.usecases import roles_usecase
from app.utils.common import generate_uuid, convert_mongo_document_to_data
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES, ROLES_INNATE_MAP

router = APIRouter()


@router.post("/",
             response_model=RoleSchema,
             summary="Role creation")
def create_role(
        role_create: RoleCreateSchema,
        current_user: UserModel = Depends(deps.get_current_user)):
    """"""
    roles_usecase.init_roles_innate()

    name = role_create.name
    # FIXME: verification permissions legitimacy
    permissions = role_create.permissions

    role = RoleModel.objects(name=name).first()
    if role is not None:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": f"role [{name}] already exists"})
    role = RoleModel(**role_create.dict(),
                     id=generate_uuid(length=26),
                     creator=current_user.id    # str
                     )
    role.save()

    roleSchema = RoleSchema(**convert_mongo_document_to_data(role))
    return roleSchema


@router.get("/",
            summary="List of roles")
def read_roles(
        current_user: UserModel = Depends(deps.get_current_user)):
    """"""
    resp = roles_usecase.admin_read_roles()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(resp))


@router.get("/{role_id}",
            response_model=RoleSchema,
            summary="Role Details")
def read_role(
        role_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """"""
    roles_usecase.init_roles_innate()

    role = RoleModel.objects(id=role_id).first()
    if role is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"role not found for [{role_id}]"})
    schema = RoleSchema(**convert_mongo_document_to_data(role))
    return schema


@router.put("/{role_id}",
            response_model=RoleSchema,
            summary="Role update")
def update_role(
        role_id: str,
        role_update: RoleUpdateSchema,
        current_user: UserModel = Depends(deps.get_current_user)):
    """"""
    roles_usecase.init_roles_innate()

    role = RoleModel.objects(id=role_id).first()
    if role is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"role not found for [{role_id}]"})
    # Determines if the target name has the same name
    updates = {k: v for k, v in role_update.dict().items() if v not in INVALID_UPDATE_VALUE_TYPES}

    # Determines whether is specified as is_default_role
    is_default_role = updates.get("is_default_role")
    if is_default_role:
        updates.pop("is_default_role", None)
        if not isinstance(is_default_role, bool):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid is_default_role type: {is_default_role}"})
        # Update only is_default_role = True
        if is_default_role is True:
            # Let's set the others to is_default_role=False， And then take this role Set to is_default_role = True
            RoleModel.objects.update(**{"is_default_role": False})
            role.is_default_role = True
            role.save()
            role.reload()

    # Determine if roles are preset： No modification allowed ADMIN
    # ROLES_INNATE = [v.get("name") for k, v in ROLES_INNATE_MAP.items()]
    if role.name == ROLES_INNATE_MAP.get("ADMIN").get("name"):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "msg": f"innate role ADMIN is forbidden to update"})

    # Judgment name
    name = updates.get("name")
    if name:
        role_other = RoleModel.objects(id__ne=role_id,
                                       name=name).first()
        if role_other is not None:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"role with same name [{name}] already exists"})
    # Judgment permissions
    permissions = updates.get("permissions")
    if permissions:
        if not isinstance(permissions, list):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid role permissions format: {permissions}"})
        for p in permissions:
            if not (isinstance(p, dict) and bool(p) is True):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid role permissions format: {permissions}"})

    try:
        if bool(updates):
            updates["updated_at"] = datetime.utcnow()
            role.update(**updates)
            # Must reload to get updated attribute
        role.save()
        role.reload()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": "failed to update role"})
    else:
        data = convert_mongo_document_to_data(role)
        schema = RoleSchema(**data)
        return schema


@router.delete("/{role_id}",
               summary="Role deletion")
def delete_role(
        role_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Role deletion，Of the associated user role Empty fields
    """
    roles_usecase.init_roles_innate()

    role = RoleModel.objects(id=role_id).first()
    if role is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"role not found for [{role_id}]"})

    # Preset roles, Disallow deletion
    ROLES_INNATE = [v.get("name") for k, v in ROLES_INNATE_MAP.items()]
    if (role.name in ROLES_INNATE) or (role.is_innate is True):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "msg": f"innate role is forbidden to delete"})

    try:
        role.delete()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to delete role [{role_id}]"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success"})
