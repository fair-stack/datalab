from fastapi import (
    APIRouter,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.models.mongo import UserModel
from app.usecases.permissions_usecase import (
    pre_check_permissions_exist,
    get_permissions_tree_data,
)


router = APIRouter()


@router.get("/tree",
            summary="Permission tree structure")
def get_permissions_tree(current_user: UserModel = Depends(deps.get_current_user)):
    """
    Gets the permission tree structure
    """
    # Determine if any preset permissions exist
    pre_check_permissions_exist()

    # Getting the tree structure
    data = get_permissions_tree_data()

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))
