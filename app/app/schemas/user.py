from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBaseSchema(BaseModel):
    name: str
    email: EmailStr
    organization: Optional[str]
    role: Optional[str]
    avatar: Optional[str]
    is_email_verified: Optional[bool] = False
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    from_source: Optional[str]


class UserInDBSchema(UserBaseSchema):
    id: Optional[str] = None
    hashed_password: Optional[str] = None
    password_strength: Optional[str] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
