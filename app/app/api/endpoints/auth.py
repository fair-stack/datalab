from datetime import timedelta

import aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api import deps
from app.core.config import settings
from app.core.jwt import create_access_token
from app.crud import crud_user
from app.forms import PasswordForgetForm, PasswordResetForm
from app.models.mongo import UserModel
from app.schemas import TokenSchema
from app.usecases import users_usecase
from app.usecases.roles_usecase import flatten_role_permissions
from app.utils.common import convert_mongo_document_to_data
from app.utils.constants import (
    CACHE_PREFIX_LOGIN,
    CACHE_PREFIX_PASSWORD_FORGET,
    CACHE_PREFIX_PASSWORD_RESET,
    CACHE_PREFIX_BearerTokenAuthBackend,
)
from app.utils.email_util import validate_email_format
from app.utils.file_util import convert_base64_str_to_bytes
from app.utils.safety_util import rsa_decrypt, check_password_strength

router = APIRouter()


@router.post("/login",
             response_model=TokenSchema,
             summary="Log in and get token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Decrypt the front-end encrypted password
    try:
        print(form_data.password)
        password = rsa_decrypt(form_data.password)
    except Exception as e:
        print(f'e: {e}')
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid password:"})

    # Note： email Derived from user input username
    email = form_data.username
    user = crud_user.authenticate(
        email=email,
        password=password
    )
    if not user:
        # return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED,
        #                     content={"msg": "Invalid credentials"})

        # Upper limit on the number of typos allowed
        FAILED_LOGIN_LIMIT = 5
        # Reach the limit，Sets the expiration time of the cache
        LOCK_DURATION_IF_EXCEED_FAILED_LOGIN_LIMIT = 60 * 60  # seconds

        # Try limits： Continuous misinput 5 time，You are allowed to try again after an hour
        try:
            redis_conn = await aioredis.StrictRedis(host=settings.REDIS_HOST,
                                                    port=settings.REDIS_PORT,
                                                    db=settings.AUTH_CACHE_DB,
                                                    encoding="utf-8",
                                                    decode_responses=True)  # Set to True，Is guaranteed to return dict is str，is bytes

            if redis_conn:
                # Return the value at key ``name``, or None if the key doesn't exist
                cache_key = f'{CACHE_PREFIX_LOGIN}_{email}'
                cache = await redis_conn.get(name=cache_key)
                # cache existence
                if cache:
                    # time
                    count_failed_login = int(cache) if cache else 0

                    # time
                    count_failed_login += 1

                    # timeReach the limit
                    if count_failed_login == FAILED_LOGIN_LIMIT:
                        # Reach the limit，Sets the expiration time of the cache: 1 h = 60 * 60 s
                        await redis_conn.set(name=cache_key,
                                             value=count_failed_login,
                                             ex=LOCK_DURATION_IF_EXCEED_FAILED_LOGIN_LIMIT)
                    elif count_failed_login > FAILED_LOGIN_LIMIT:
                        #
                        print("login_for_access_token: excessive failed login, locked for 60 min before try again")
                        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                            content={"msg": f"A password error has been reached {FAILED_LOGIN_LIMIT} time，Please visit the 60 min Retry after"})
                    else:
                        await redis_conn.set(name=cache_key, value=count_failed_login)
                # cache existence： Creating a cache
                else:
                    await redis_conn.set(name=cache_key, value=1)   # Initial value 1

                # Close the link
                await redis_conn.close()
            else:
                #
                print(f'login_for_access_token: no cache connection')
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": "Account password is incorrect"})
        except Exception as e:
            print(f"login_for_access_token: {e}")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Account password is incorrect"})
    else:
        # Role update: Role to flush the cache
        try:
            redis_conn = await aioredis.StrictRedis(host=settings.REDIS_HOST,
                                                    port=settings.REDIS_PORT,
                                                    db=settings.AUTH_CACHE_DB,
                                                    encoding="utf-8",
                                                    decode_responses=True)  # Set to True，Is guaranteed to return dict is str，is bytes
            if redis_conn:
                cache_key = f'{CACHE_PREFIX_BearerTokenAuthBackend}_{email}'
                await redis_conn.hset(name=cache_key,
                                      key="role",
                                      value=user.role)
                # Close the link
                await redis_conn.close()
            else:
                print(f"login_for_access_token: no cache connection")
        except Exception as e:
            print(f"login_for_access_token: {e}")

        # Email verification status
        if not crud_user.is_email_verified(user):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "Please complete the email verification first，Log in again"})
        # Online status
        if not crud_user.is_active(user):
            # return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
            #                     content={"msg": "Inactive user is forbidden"})
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "The user has been logged off，Disable login"})

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/#Return%20the%20token

    return {
        "access_token": create_access_token(data={"username": user.name, "email": user.email},
                                            expires_delta=access_token_expires),
        "token_type": "bearer"
    }


@router.post("/passwordForget",
             summary="Forgot password")
async def forget_password(background_tasks: BackgroundTasks,
                          password_forget_form: PasswordForgetForm = Depends()):
    """
    Forgot password，Send a password reset email
    :return:
    """
    # Verify that the email is formatted correctly
    email = password_forget_form.email
    if not validate_email_format(email):
        print(f'Invalid email address: {email}')
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Invalid email address [{email}]"})

    # existence
    user = UserModel.objects(name=password_forget_form.username,
                             email=password_forget_form.email).first()
    if not user:
        # return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"msg": "User not found"})
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"msg": "existence"})

    # Check the email delivery interval：30s Duplicate email is prohibited
    try:
        redis_conn = await aioredis.StrictRedis(host=settings.REDIS_HOST,
                                                port=settings.REDIS_PORT,
                                                db=settings.AUTH_CACHE_DB,
                                                encoding="utf-8",
                                                decode_responses=True)  # Set to True，Is guaranteed to return dict is str，is bytes

        # Return the value at key ``name``, or None if the key doesn't exist
        cache_key = f'{CACHE_PREFIX_PASSWORD_FORGET}_{email}'
        token_cache = await redis_conn.get(name=cache_key)
        if token_cache:
            # token_cache existence，Disallow further operation
            print("password_reset_email forbidden to send during 30s")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "Password reset email has been sent，30sPlease do not click again"})
    except Exception as e:
        print(f"e: {e}")

    # Sending an email
    background_tasks.add_task(users_usecase.send_password_reset_email,
                              username=password_forget_form.username,
                              to_addr=password_forget_form.email
                              )
    # Cache write，Note key，With expiration time
    try:
        expire = settings.RESET_PASSWORD_EMAIL_SENT_FREQUENCY_SECONDS  # seconds
        await redis_conn.set(name=cache_key, value=email, ex=expire)
        await redis_conn.close()
    except Exception as e:
        print(f'e: {e}')

    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})


@router.post("/passwordReset",
             summary="Reset Password")
async def reset_password(password_reset_form: PasswordResetForm = Depends()):
    """
    Reset Password，Reset Password（Carry aroundtoken）； The frontend resets the user password + token Send to this interface

    :return:
    """

    token = password_reset_form.token
    try:
        redis_conn = await aioredis.StrictRedis(host=settings.REDIS_HOST,
                                                port=settings.REDIS_PORT,
                                                db=settings.AUTH_CACHE_DB,
                                                encoding="utf-8",
                                                decode_responses=True)  # Set to True，Is guaranteed to return dict is str，is bytes

        # Return the value at key ``name``, or None if the key doesn't exist
        cache_key = f"{CACHE_PREFIX_PASSWORD_RESET}_{token}"
        token_cache = await redis_conn.get(name=cache_key)
        if token_cache:
            # token_cache existence，Disallow further operation
            print("email token cannot be re-used")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "The password reset email link is invalid"})
    except Exception as e:
        print(f"e: {e}")

    # Decrypt the front-end encrypted password
    try:
        password = rsa_decrypt(password_reset_form.password)
    except Exception as e:
        print(f'e: {e}')
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid password"})

    # Verify password strength
    code, msg, _ = check_password_strength(password)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})

    code, msg = deps.reset_password_with_verify_token_validity(token=password_reset_form.token,
                                                               password=password)

    # Cache write token，With expiration time
    try:
        expire = settings.RESET_PASSWORD_TOKEN_EXPIRE_MINUTES * 60  # seconds
        await redis_conn.set(name=cache_key, value=token, ex=expire)
        await redis_conn.close()
    except Exception as e:
        print(f'e: {e}')

    print(f'code: {code}')
    print(f'msg: {msg}')
    if code == status.HTTP_200_OK:
        # Reset Password
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success"})
    else:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "invalid email"})


@router.get("/emailVerify",
            summary="Verify email validity")
def verify_email(token: str):
    code, msg = deps.verify_register_email_token_validity(token)
    print(f'code: {code}')
    print(f'msg: {msg}')
    if code == status.HTTP_200_OK:
        # The interface specified by the backhop front end URL
        url = f"http://{settings.SERVER_HOST}/sublogin"
        return RedirectResponse(url=url)
    else:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "invalid email"})


@router.get("/me",
            summary="Current logged-in user information")
def read_me(
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Retrieve user
    """
    if current_user is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"current_user not found"})
    _data = convert_mongo_document_to_data(current_user)
    # avatar
    # if _data.get("avatar") is not None:
    #     _data['avatar'] = get_img_b64_stream(_data.get("avatar"))
    # else:
    #     _data['avatar'] = ''
    _data['avatar'] = convert_base64_str_to_bytes(_data.get("avatar"))

    role_id = None
    role_name = None
    flat_permissions = None
    permissions = None
    if current_user.role is not None:
        # document
        role = current_user.role
        permissions = role.permissions
        # permissions Verify validity
        flat_permissions = flatten_role_permissions(permissions)
        role_id = role.id
        role_name = role.name
    _data['role_id'] = role_id
    _data['role_name'] = role_name
    _data['flat_permissions'] = flat_permissions
    _data['permissions'] = permissions

    # Remove information that is not needed，Hold on
    data = dict()
    data['id'] = _data.get('id')
    data['name'] = _data.get('name')
    data['avatar'] = _data.get('avatar')
    data["flat_permissions"] = _data.get("flat_permissions")
    for p in data['flat_permissions']:
        # Hold on `id`，The frontend needs to be based on `id`
        p.pop("code", None)
        p.pop("name", None)
        p.pop("uri", None)

    # return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(_data))
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(data))
