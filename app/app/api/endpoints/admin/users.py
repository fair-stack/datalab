from datetime import datetime
from typing import Union, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from mongoengine import Q

from app.api import deps
from app.forms import UserCreateForm, AdminUserUpdateForm
from app.models.mongo import RoleModel, UserModel
from app.usecases import users_usecase
from app.utils.common import convert_mongo_document_to_data
from app.utils.constants import ROLES_INNATE_MAP
from app.utils.file_util import convert_base64_str_to_bytes

router = APIRouter()


@router.post("/",
             summary="User creation")
async def create_user(background_tasks: BackgroundTasks,
                      form: UserCreateForm = Depends()):
    """
    Create new user.
    """
    code, msg = users_usecase.create_user(form)
    if code == status.HTTP_200_OK:
        background_tasks.add_task(users_usecase.send_email_verification_email_in_signup,
                                  username=form.name,
                                  to_addr=form.email
                                  )
    return JSONResponse(status_code=code, content={"msg": msg})


@router.get("/",
            summary="List of users")
def read_users(
        q: Union[str, None] = None,
        role: Union[str, None] = None,
        is_active: Optional[Union[bool, str]] = '',
        page: int = 0,
        size: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Retrieve users.
    """
    skip = page * size

    # query = Q(deleted__ne=True)
    query = None

    if q:
        query = Q(name__icontains=q)

    if role:
        if query is not None:
            query = query & Q(role=role)
        else:
            query = Q(role=role)

    if isinstance(is_active, bool):
        if query is not None:
            query = query & Q(is_active=is_active)
        else:
            query = Q(is_active=is_active)

    # User statistics
    count_all = UserModel.objects().count()
    count_active = UserModel.objects(is_active=True).count()
    count_inactive = UserModel.objects(is_active__ne=True).count()

    if query is not None:
        total = UserModel.objects(query).count()
        users = UserModel.objects(query).order_by("-created_at")[skip: skip + size]
    else:
        total = UserModel.objects.count()
        users = UserModel.objects.order_by("-created_at")[skip: skip + size]

    data = []
    for user in users:
        tmp = convert_mongo_document_to_data(user)
        tmp["role_name"] = user.role.name if user.role is not None else ""
        tmp["is_self"] = user.id == current_user.id
        # Remove sensitive fields
        tmp = users_usecase.filter_out_user_sensitive_field(tmp)

        data.append(tmp)

    content = {"msg": "success",
               "total": total,  # Paging with，Based on retrieval criteria
               "count_all": count_all,
               "count_active": count_active,
               "count_inactive": count_inactive,
               "data": data}
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/{user_id}",
            summary="User details")
async def read_user(
        user_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Retrieve user
    """
    code, msg, data = await users_usecase.read_user(user_id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    content = {"msg": "success", "data": data}
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(content))


@router.put("/{user_id}",
            summary="User to update")
async def update_user(
        user_id: str,
        form: AdminUserUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)):
    """
        The current user（As an administrator）Change other users（It could be yourself）Status information of:
            - is_active
            - role
    """
    # Determines if the user exists
    user = UserModel.objects(id=user_id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"user not found for {user_id}"})

    # Update role
    role_id = form.role
    if role_id:
        # role existence
        role = RoleModel.objects(id=role_id).first()
        if role is None:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f" invalid role_id {role_id}"})
        # Update role, And if the logged-in user
        user.role = role
        # If role Is the preset super administrator， Update is_superuser
        if role.name.upper() == ROLES_INNATE_MAP.get("ADMIN").get("name"):
            user.is_superuser = True

    # Update is_active
    is_active = form.is_active
    if is_active is not None:
        if not isinstance(is_active, bool):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid is_active type: {is_active}"})
        # Update is_active, And if the logged-in user
        user.is_active = is_active

    # Update，And save it
    user.updated_at = datetime.utcnow()
    user.save()
    user.reload()

    data = convert_mongo_document_to_data(user)
    # if data.get("avatar") is not None:
    #     data['avatar'] = get_img_b64_stream(data.get("avatar"))
    # else:
    #     data['avatar'] = ''
    data['avatar'] = convert_base64_str_to_bytes(data.get("avatar"))

    # Remove sensitive fields
    data = users_usecase.filter_out_user_sensitive_field(data)

    content = {"msg": "success", "data": data}
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(content))


@router.delete("/{user_id}",
               summary="User deletion")
def delete_user(
        user_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    """

    user = UserModel.objects(id=user_id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"user not found for {user_id}"})

    # User deletion：Only deactivated users can be deleted（Active users must be deactivated first）
    if user.is_active:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={"msg": f"user is active, forbidden to delete: {user_id}"})

    try:
        # Illogical deletion
        user.delete()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to delete user: [{user_id}]"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success"})
