from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.core.security import get_password_hash
from app.forms import UserCreateForm, UserUpdateForm
from app.models.mongo import UserModel
from app.usecases import users_usecase
from app.utils.common import convert_mongo_document_to_data
from app.utils.constants import INVALID_UPDATE_VALUE_TYPES
from app.utils.file_util import (
    convert_base64_str_to_bytes,
    convert_uploaded_img_to_b64_stream_str,
)
from app.utils.safety_util import check_password_strength, rsa_decrypt

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


@router.get("/{user_id}",
            summary="User details（Personal Center）")
async def read_user(
        user_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Retrieve user
    """
    # Must match the currently logged-in user
    if user_id != current_user.id:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "msg": f"current_user [{current_user.id}] is not user [{user_id}], read is forbidden"})

    code, msg, data = await users_usecase.read_user(user_id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    content = {"msg": "success", "data": data}
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(content))


@router.put("/{user_id}",
            summary="User to update（Personal Center）")
async def update_user(
        user_id: str,
        form: UserUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)):
    """
        Logged in user，Change your information（name，password，avatar Etc.）
    """
    # Must match the currently logged-in user
    if user_id != current_user.id:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                            content={
                                "msg": f"current_user [{current_user.id}] is not user [{user_id}], update is forbidden"})

    # Determines if the user exists
    user = UserModel.objects(id=user_id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"user not found for {user_id}"})

    # name
    name = form.name
    if name:
        # Judgment
        if name in INVALID_UPDATE_VALUE_TYPES:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid name: {name}"})
        user.name = name

    # organization
    organization = form.organization
    if organization:
        # Judgment
        if organization in INVALID_UPDATE_VALUE_TYPES:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid organization: {organization}"})
        user.organization = organization

    # password： Must generate a new hashed_password，And update the corresponding fields
    form_password = form.password
    if form_password:
        # Judgment
        if form_password in INVALID_UPDATE_VALUE_TYPES:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid password"})
        # Decrypt the front-end encrypted password
        try:
            password = rsa_decrypt(form_password)
        except Exception as e:
            print(f'e: {e}')
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid password"})

        print(f'form_password: {form_password}')
        print(f'password: {password}')

        # Verify password strength
        code, msg, strength = check_password_strength(password)
        if code != status.HTTP_200_OK:
            return JSONResponse(status_code=code, content={"msg": msg})
        else:
            # Generation hashed_password
            user.hashed_password = get_password_hash(password)
            # Update password strength
            user.password_strength = strength

    # avatar
    file = form.avatar
    if file:
        # storage_path = Path(settings.BASE_DIR, settings.CONFIGS_PATH, "user", current_user.id)
        # if not (storage_path.exists() and storage_path.is_dir()):
        #     storage_path.mkdir(parents=True)
        #
        # dest_path = Path(storage_path, file.filename)
        # # As the name file exists，Then it covers
        # # file.file is `file-like` object
        # chunked_copy(file.file, dest_path)
        # user.avatar = str(dest_path.resolve())
        # print(type(convert_uploaded_img_to_b64_stream(file.file)))
        user.avatar = convert_uploaded_img_to_b64_stream_str(file.file)

    # Update time，And save it
    user.updated_at = datetime.utcnow()
    user.save()
    user.reload()

    # userInDBSchema = UserInDBSchema(**convert_mongo_document_to_data(user))
    # data = userInDBSchema.dict()
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
