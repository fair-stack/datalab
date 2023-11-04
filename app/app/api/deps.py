from datetime import datetime
from typing import Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from mongoengine import Document
from pydantic import ValidationError

from app.core.security import get_password_hash
from app.crud import crud_user
from app.core.config import settings
from app.core.jwt import ALGORITHM
from app.models.mongo import UserModel
from app.schemas import TokenPayLoadSchema, RegisterEmailVerifyTokenPayLoadSchema, PasswordResetTokenPayLoadSchema

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f'{settings.API_STR}/login'
)


def verify_logged_in(token: str = Depends(reusable_oauth2)) -> bool:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        # {'username': xx, 'email': xx, 'sub': xx, 'exp': xx}
        token_data = TokenPayLoadSchema(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials"
        )
    user = crud_user.get_user_by_email(email=token_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return True


def get_current_user(token: str = Depends(reusable_oauth2)) -> Document:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        # print(f'payload: {payload}')
        # {'username': xx, 'email': xx, 'sub': xx, 'exp': xx}
        token_data = TokenPayLoadSchema(**payload)
        # print(f"token_data: {token_data}")
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    # user = crud_user.get_user_by_email(email=token_data.email)
    user = UserModel.objects(email=token_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_active_user(current_user: UserModel = Depends(get_current_user)):
    if not crud_user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(current_user: UserModel = Depends(get_current_active_user)):
    if not crud_user.is_superuser(current_user):
        raise HTTPException(status_code=400, detail="The user doesn't have enough privileges")
    return current_user


def verify_register_email_token_validity(token: str) -> Tuple[int, str]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        print(f'payload: {payload}')
        # {'username': xx, 'email': xx, 'sub': xx, 'exp': xx}
        token_data = RegisterEmailVerifyTokenPayLoadSchema(**payload)
        print(f"token_data: {token_data}")
    except (jwt.JWTError, ValidationError):
        code = status.HTTP_401_UNAUTHORIZED
        msg = "invalid credentials"
        return code, msg
    #
    user = UserModel.objects(email=token_data.email).first()
    if not user:
        code = status.HTTP_404_NOT_FOUND
        msg = f"User not found for email: {token_data.email}"
    else:
        user.is_email_verified = True
        user.updated_at = datetime.utcnow()
        user.save()
        #
        code = status.HTTP_200_OK
        msg = f'email is valid: {token_data.email}'
    return code, msg


def reset_password_with_verify_token_validity(token: str, password: str) -> Tuple[int, str]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        print(f'payload: {payload}')
        # {'username': xx, 'email': xx, 'sub': xx, 'exp': xx}
        token_data = PasswordResetTokenPayLoadSchema(**payload)
        print(f"token_data: {token_data}")
    except (jwt.JWTError, ValidationError):
        code = status.HTTP_401_UNAUTHORIZED
        msg = "invalid credentials"
        return code, msg

    # Judgment password
    if not isinstance(password, str):
        code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid password type"
        return code, msg

    user = UserModel.objects(name=token_data.username,
                             email=token_data.email).first()
    if not user:
        code = status.HTTP_404_NOT_FOUND
        msg = f"User not found for email: {token_data.email}"
    else:
        user.hashed_password = get_password_hash(password)
        user.updated_at = datetime.utcnow()
        user.save()
        #
        code = status.HTTP_200_OK
        msg = f'successful password reset for: {token_data.email}'
    return code, msg
