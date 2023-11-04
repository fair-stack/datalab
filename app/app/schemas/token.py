from typing import Optional

from pydantic import BaseModel


class TokenSchema(BaseModel):
    access_token: str
    token_type: str


class TokenPayLoadSchema(BaseModel):
    username: str = ""
    email: str


class RegisterEmailVerifyTokenPayLoadSchema(BaseModel):
    username: str = ""
    email: str


class PasswordResetTokenPayLoadSchema(BaseModel):
    username: str
    email: str
