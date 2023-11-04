from datetime import datetime, timedelta

from jose import jwt

from app.core.config import settings


ALGORITHM = "HS256"
ACCESS_TOKEN_JWT_SUBJECT = "ACCESS_TOKEN_JWT_SUBJECT"
EMAIL_VERIFY_TOKEN_JWT_SUBJECT = "EMAIL_VERIFY_TOKEN_JWT_SUBJECT"
RESET_PASSWORD_TOKEN_JWT_SUBJECT = "RESET_PASSWORD_TOKEN_JWT_SUBJECT"


def create_access_token(*, data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    # expire
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Update to_encode
    to_encode.update({"exp": expire, "sub": ACCESS_TOKEN_JWT_SUBJECT})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_email_verify_token(*, data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    # expire
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.EMAIL_VERIFY_TOKEN_EXPIRE_MINUTES)
    # Update to_encode
    to_encode.update({"exp": expire, "sub": EMAIL_VERIFY_TOKEN_JWT_SUBJECT})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_password_reset_token(*, data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    # expire
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.RESET_PASSWORD_TOKEN_EXPIRE_MINUTES)
    # Update to_encode
    to_encode.update({"exp": expire, "sub": RESET_PASSWORD_TOKEN_JWT_SUBJECT})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
