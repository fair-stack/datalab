import json
from datetime import timedelta

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.core.jwt import create_access_token
from app.forms import UserCreateForm
from app.models.mongo import RoleModel, UserModel
from app.usecases import users_usecase
from app.utils.constants import ROLES_INNATE_MAP
from app.utils.email_util import validate_email_format

router = APIRouter()


@router.get("/callback/",  # FIXME: Whether to bring /
            summary="Tech Cloud authentication callback")
async def umt_authorize_callback(code: str):
    """
    This interface is umt The callback address configured when requesting access to the application，namely redirect_URI， Used of accepting. authorization code.
    Get hold of authorization code after，after URI To get a pass Access_Token：
        - https://passport.escience.cn/oauth2/token
            - Submission method：POST
                Conten-Type: application/x-www-form-urlencoded
            - The submission parameters are:
                client_id: YOUR_CLIENT_ID   //Client side ID
                client_secret: YOUR_CLIENT_SECRET
                grant_type:authorization_code   //Fixed value
                redirect_uri: YOUR_REGISTERED_REDIRECT_URI  //Callback address in the request form
                code:code   //In the second step, it is transmitted back code Value of， Notefor safety's sake，code. code Visit this link several times

        - .：
            {
                "access_token":  "SlAV32hkKG",
                "expires_in":  3600,
                “refresh_token:  ”ASAEDFIkie876”,
                ”userInfo”: {
                    “umtId”:  12,
                     “truename”:  ”yourName”,
                    ” type”:  ”umtauth”,
                    ”securityEmail”: ” securityEmail”,
                    ”cstnetIdStatus”: ”cstnetIdStatus”,
                    ”cstnetId”: ”yourEmail”,
                    “passwordType”:” password_umt”,
                    ”secondaryEmails”:[“youremail1”, “youremail2”]
                }   //Note，Here for convenience，userInfo The value is displayed as json Structure，The actual return value is json String（By double quotes""Carry out the parcel）Types，Need to be converted to json after.
            }

             Parameter Description：
                umtId：correspondence umt On the inside id No.
                truename：User's real name
                type：Scope of account umt,coremail,uc
                securityEmail：Confidential email address
                cstnetIdStatus：Master account activation status，namely， Optional values： active-Activated， temp-..
                passwordType: Types
                cstnetId：User's primary email address
                secondaryEmails：Auxiliary Mailbox Mailbox，It is not open to set up auxiliary mailbox api

        When requesting access token endpoint: https://passport.escience.cn/oauth2/token An error occurred while，
        Add to the return parameter error=errorcodestatus

    FIXME: In the document YOUR_REGISTERED_REDIRECT_URI/?code=CODE with “/”，Registrationwith？

    :param code: authorization code
    :return:
    """
    # FIXME: Registration UMT The obtained APP_KEY, APP_SECRET
    UMT_CLIENT_ID = "UMT_APP_KEY"
    UMT_CLIENT_SECRET = "UMT_APP_SECRET"
    UMT_REGISTERED_REDIRECT_URI = "UMT_REGISTERED_REDIRECT_URI"
    UMT_TOKEN_URI = "https://passport.escience.cn/oauth2/token"

    # payload
    data = {
        "client_id": UMT_CLIENT_ID,
        "client_secret": UMT_CLIENT_SECRET,
        "grant_type": "authorization_code",  # Fixed value
        "redirect_uri": UMT_REGISTERED_REDIRECT_URI,  # UMT Callback address in the request form
        "code": code,
    }

    #
    try:
        session = requests.session()
        r = session.post(url=UMT_TOKEN_URI, data=data)

        if r.status_code == 200:
            content = r.json()
            # Determine if an error has occurred： Add to the return parameter error=errorcodestatus
            if "error" in content:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content=jsonable_encoder(content))
            # normal，Parse the required data
            for key in ['access_token', 'expires_in', 'refresh_token']:
                value = content.get(key)
                if not value:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content=jsonable_encoder({"msg": f"{key} is missing: {content}"}))
            #
            access_token = content.get("access_token")
            expires_in = content.get("expires_in")
            refresh_token = content.get("refresh_token")

            # userInfo The value is displayed as json Structure，The actual return value is json String
            userInfo = content.get("userInfo")
            if not userInfo:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content=jsonable_encoder({"msg": f"userInfo is missing: {content}"}))
            userInfo = json.loads(userInfo)
            for key in ['umtId', 'truename', 'cstnetId', 'cstnetIdStatus']:
                value = content.get(key)
                if not value:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content=jsonable_encoder({"msg": f"userInfo.{key} is missing: {content}"}))
            umtId = userInfo.get("umtId")
            userName = userInfo.get("truename")
            email = userInfo.get("cstnetId")
            userStatus = userInfo.get("cstnetIdStatus")
            if userStatus != 'active':
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid userStatus: {userStatus}"})

            # Establish UserModel
            default_role = RoleModel.objects(is_default_role=True).first()
            if default_role is None:
                default_role = RoleModel.objects(
                    id=ROLES_INNATE_MAP.get("USER_SENIOR", {}).get("code", "USER_SENIOR")).first()
            #
            try:
                userModel = UserModel(
                    id=umtId,
                    name=userName,
                    email=email,
                    role=default_role,
                    is_email_verified=True,
                    is_active=True,
                    is_superuser=False,
                    from_source="umt"
                )
                userModel.save()
                userModel.reload()
                #
                access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                token = create_access_token(
                    data={
                        "username": userName,
                        "email": email
                    },
                    expires_delta=access_token_expires
                )
                redirect_url = f"http://{settings.SERVER_HOST}/index?token={token}"
                return RedirectResponse(url=redirect_url)
            except Exception as e:
                print(f'e: {e}')
                redirect_url = f"http://{settings.SERVER_HOST}/index"
                return RedirectResponse(url=redirect_url)
        else:
            status_code = r.status_code
            msg = r.reason
            return JSONResponse(status_code=status_code,
                                content={"msg": msg})
    except Exception as e:
        print(f'exception: {e}')
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"failed to parse umt redirect info: {e}"})


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
