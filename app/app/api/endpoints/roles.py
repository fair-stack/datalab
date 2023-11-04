from typing import List

from fastapi import (
    APIRouter,
    Depends,
)

from app.api import deps
from app.models.mongo import UserModel
from app.schemas import RoleBaseSchema
from app.usecases import roles_usecase

router = APIRouter()


@router.get("/",
            response_model=List[RoleBaseSchema],
            summary="List of roles")
def read_roles():
    """"""
    resp = roles_usecase.read_roles()
    return resp
