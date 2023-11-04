# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:main
@time:2022/06/27
"""
import aioredis
from fastapi import status
from jose import jwt
from pydantic import ValidationError
from starlette.authentication import AuthenticationBackend, AuthenticationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.jwt import ALGORITHM
from app.crud import crud_user
from app.models.mongo import RoleModel
from app.schemas import TokenPayLoadSchema
from app.usecases.roles_usecase import flatten_role_permissions
from app.utils.constants import (
    CACHE_PREFIX_BearerTokenAuthBackend,
    ENDPOINTS_FOR_UNAUTHORIZED,
    PERMISSION_MAP,
)


class BearerTokenAuthBackend(AuthenticationBackend):
    """
    This is a custom auth backend class that will allow you to authenticate your request,
    and return a tuple(auth, user)

    ref:
    - https://github.com/tiangolo/fastapi/issues/3043
    - https://www.starlette.io/authentication/
    """
    async def authenticate(self, request: Request):
        # print('---------------------------------------')
        # print(f'BearerTokenAuthBackend')

        # skip `path` for generating token
        if request.url.path in ENDPOINTS_FOR_UNAUTHORIZED:
            return

        if "Authorization" not in request.headers:
            return
        authorization: str = request.headers.get("Authorization")
        if not authorization:
            return
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            return
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[ALGORITHM]
            )
            # {'username': xx, 'email': xx, 'sub': xx, 'exp': xx}
            token_data = TokenPayLoadSchema(**payload)
        except (jwt.JWTError, ValidationError):
            raise AuthenticationError('Invalid JWT Token: failed to decode')

        # email
        email = token_data.email

        user = crud_user.get_user_by_email(email=email)     # UserInDBSchema
        if not user:
            raise AuthenticationError('Invalid JWT Token: user not found')
        else:
            # Email verification status
            if not user.is_email_verified:
                raise AuthenticationError('The user has not completed email validation，Disable login')
            # Online status
            if not user.is_active:
                raise AuthenticationError('The user has been logged off，Disable login')
            # Is the role updated?: Compare the current role with the cached role，If you don't agree，Force a re-login
            try:
                redis_conn = await aioredis.StrictRedis(host=settings.REDIS_HOST,
                                                        port=settings.REDIS_PORT,
                                                        db=settings.AUTH_CACHE_DB,
                                                        encoding="utf-8",
                                                        decode_responses=True)  # Set to True，Is guaranteed to return dict is str，is bytes
            except Exception as e:
                print(f"BearerTokenAuthBackend: {e}")

            if redis_conn:
                cache_key = f'{CACHE_PREFIX_BearerTokenAuthBackend}_{email}'
                cache_role = await redis_conn.hget(name=cache_key, key="role")  # for role_id

                # cache existence
                if cache_role:
                    # comparison
                    if cache_role != user.role:
                        raise AuthenticationError('User roles have changed，Must log in again')

                # cache existence： Creating a cache
                else:
                    await redis_conn.hset(name=cache_key,
                                          key="role",
                                          value=user.role)

                # Close the link
                await redis_conn.close()

        #
        return authorization, user


def on_token_auth_error(request: Request, exc: Exception):
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"error": str(exc)}, )


# FIXME: to be registered
class PermissionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:

        print('---------------------------------------')
        print(f'PermissionAuthMiddleware')
        print(f'request_path: {request.url.path}')

        # login Path ignoring
        response = await call_next(request)
        print(f"request_path in ENDPOINTS_FOR_UNAUTHORIZED: {request.url.path in ENDPOINTS_FOR_UNAUTHORIZED}")
        if request.url.path in ENDPOINTS_FOR_UNAUTHORIZED:
            return response

        # Getting the logged-in user
        user = request.user
        # print(f'user: {user}')
        if not user:
            response = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED,
                                    content={"msg": "failed to auth perm: no relevant user"})
            return response
        try:
            # get role
            role = user.role
            if not role:
                print(f'role invalid: {role}')
                return response
            # print(f'role type: {type(role)}')
            # print(f'role: {role}')
            roleModel = RoleModel.objects(id=role).first()
            if not roleModel:
                print(f'roleModel not exist: {role}')
                return response
        except Exception as e:
            print(f"exception about role")
            print(f"e: {e}")
            return response

        try:
            # get permissions = flatten_role_permissions(role.permissions)
            # get role model
            permissions = roleModel.permissions
            flat_permissions = flatten_role_permissions(permissions)
            # print(f'permissions: {permissions}')
            # print(f'flat_permissions: {flat_permissions}')

            if flat_permissions is None:
                return response
        except Exception as e:
            print(f"exception about permissions")
            print(f'e: {e}')
            return response

        try:
            # get path = request.url.path
            request_path = request.url.path  # for /a/b/{c}?d=xx when， path Will include path_params, But not including query_params
            # existence path_params，You strip it off
            if request.path_params not in [None, {}]:
                for k, v in request.path_params.items():
                    # request_path = request_path.strip(v)
                    request_path = request_path.replace(v, "")

            print(f'request_path: {request_path}')

            # Judgment path isno path_list： is，Move on to the next step； no，Return response
            Paths_Limited = [v.get("uri") for k, v in PERMISSION_MAP.items() if v.get("uri") not in ["", None]]
            # Flip over，Make sure the submenu is in the front； for uri long，when，Compare submenus first，The parent menu is then compared up
            Paths_Limited.reverse()

            # Judgment： isno
            contain_path_limit = False
            if request_path in Paths_Limited:
                contain_path_limit = True
            # for path_limit in Paths_Limited:
            #     if path_limit in request_path:
            #         contain_path_limit = True
            #         break
            # The request path is not in the restricted list，Then let it go
            if contain_path_limit is False:
                response = await call_next(request)
                return response
            else:
                # The request path is in the restricted list
                # Flip over permissions，Same reason as above（Flip over Paths_Limited）
                flat_permissions.reverse()
                # Filtering，Only keep checked=True
                flat_permissions = [p for p in flat_permissions if p.get("checked") is True]
                # traversal permissions，Judgment path existence，Release of；no，Release of
                valid = False
                for perm in flat_permissions:
                    if perm.get("uri") == request_path:
                        print(f'uri: {request_path}')
                        valid = True
                        break
                print(f'permitted: {valid}')
                if valid is True:
                    response = await call_next(request)
                else:
                    response = JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                                            content={
                                                "msg": f"forbidden to access this request path: {request.method} {request_path}"})
                return response
        except Exception as e:
            print(f"e: {e}")
            return response
