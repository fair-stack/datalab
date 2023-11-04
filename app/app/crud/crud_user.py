from datetime import datetime
from typing import Optional

from fastapi import status

from app.core.security import verify_password, get_password_hash
from app.forms import UserCreateForm
from app.models.mongo import UserModel, RoleModel
from app.models.mongo.resources import StorageResourceAllocatedModel, StorageResourceModel, QuotaResourceModel, UserQuotaModel
from app.schemas import UserInDBSchema
from app.utils.common import convert_mongo_document_to_data
from app.utils.common import generate_uuid
from app.utils.constants import ROLES_INNATE_MAP
from app.utils.safety_util import rsa_decrypt, check_password_strength


def create_user_via_form(form: UserCreateForm) -> Optional[UserInDBSchema]:
    # default_role
    default_role = RoleModel.objects(is_default_role=True).first()
    if default_role is None:
        default_role = RoleModel.objects(id=ROLES_INNATE_MAP.get("USER_SENIOR", {}).get("code", "USER_SENIOR")).first()

    # Decrypt the front-end encrypted password
    try:
        password = rsa_decrypt(form.password) if form.password is not None else None
    except Exception as e:
        print(f"create_user_via_form: {e}")
        return None

    # Verify password strength
    code, msg, strength = check_password_strength(password)
    if code != status.HTTP_200_OK:
        print(f"create_user_via_form: {msg}")
        return None

    user = UserModel(
        id=generate_uuid(length=26),
        name=form.name,
        email=form.email,
        organization=form.organization,
        hashed_password=get_password_hash(password),
        password_strength=strength,
        is_email_verified=False,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    StorageResourceAllocatedModel(id=generate_uuid(),
                                  user="abea7aa40e0d4e0d99d217da89",
                                  allocated_storage_size=StorageResourceModel.objects.first().newcomer,
                                  allocated_user=user.id).save()
    UserQuotaModel(id=generate_uuid(),
                   user=user,
                   quota=QuotaResourceModel.objects.first().newcomer,
                   balance=QuotaResourceModel.objects.first().newcomer).save()
    user.role = default_role
    try:
        user.save()
        user.reload()
    except Exception as e:
        # There is a possibility that duplicated unique key
        print(f"create_user_via_form: {e}")
        return None
    else:
        _data = convert_mongo_document_to_data(user)
        userInDBSchema = UserInDBSchema(**_data)
        return userInDBSchema


def get_user(pk: str) -> Optional[UserInDBSchema]:
    user = UserModel.objects(id=pk).first()
    if user is not None:
        _data = convert_mongo_document_to_data(user)
        userInDBSchema = UserInDBSchema(**_data)
        return userInDBSchema
    else:
        return None


def get_user_by_name(name: str) -> Optional[UserInDBSchema]:
    user = UserModel.objects(name=name).first()
    if user is not None:
        _data = convert_mongo_document_to_data(user)
        userInDBSchema = UserInDBSchema(**_data)
        return userInDBSchema
    else:
        return None


def get_user_by_email(email: str) -> Optional[UserInDBSchema]:
    """
    Note: email is unique
    :param email:
    :return:
    """
    user = UserModel.objects(email=email).first()
    if user is not None:
        _data = convert_mongo_document_to_data(user)
        userInDBSchema = UserInDBSchema(**_data)
        return userInDBSchema
    else:
        return None


def authenticate(email: str, password: str):
    user = get_user_by_email(email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def is_email_verified(user: UserModel) -> bool:
    return user.is_email_verified


def is_active(user: UserModel) -> bool:
    return user.is_active


def is_superuser(user: UserModel) -> bool:
    return user.is_superuser
