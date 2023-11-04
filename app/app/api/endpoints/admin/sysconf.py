from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.core.config import settings
from app.forms import (
    EmailConfUpdateForm,
)
from app.models.mongo import (
    EmailConfModel,
    UserModel,
)
from app.usecases import sysconf_usecase
from app.utils.common import generate_uuid, convert_mongo_document_to_data
from app.utils.email_util import send_email_via_default_smtp_server, validate_email_format
from app.utils.safety_util import rsa_decrypt

router = APIRouter()


EMAIL_CONF_KEYS = ['id', 'is_default', 'is_selected', 'name', 'use_tls', 'port', 'host', 'user', 'password_encrypted', 'created_at']


@router.post("/emailconf/test",
             summary="System mail configuration test")
def test_emailconf(
        receiver: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    System mail configuration test

    :param receiver:
    :param current_user:
    :return:
    """
    try:
        emailConf = EmailConfModel.objects(is_default=False, is_selected=True).first()
        if emailConf is not None:
            msg_from = emailConf.user
        else:
            msg_from = settings.SMTP_USER

        msg = MIMEMultipart()
        msg['Subject'] = Header('DataLab Email service configuration validation', 'utf-8')
        msg['From'] = Header(msg_from)

        host = settings.SERVER_HOST

        html = f"""\
        <html>
          <body>
            <p>This is a test email，Welcome to useDataLab.
            <br/>
            <br/>
               <a href="http://{host}/login">Click me.</a>
            </p>
          </body>
        </html>
        """
        part1 = MIMEText(html, 'html')
        msg.attach(part1)

        receivers = [receiver]

        send_email_via_default_smtp_server(to_addrs=receivers, msg=msg)

    except Exception as e:
        print(f'e: {e}')
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"The mail service is misconfigured，Please check: {e}"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})


@router.put("/emailconfs/{conf_id}",
            summary="System mail configuration update")
def update_emailconf(
        conf_id: str,
        form: EmailConfUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    System mail configuration update

    :param conf_id:
    :param form:
    :param current_user:
    :return:
    """
    # TODO： verification port and ssl Protocol correspondence:  ssl Default 465， non ssl Default 25

    # Querying
    emailConfModel = EmailConfModel.objects(id=conf_id).first()
    if not emailConfModel:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Invalid Mail service [{conf_id}]"})

    # First, get is_selected
    is_selected = form.is_selected
    if is_selected is not None:
        if not isinstance(is_selected, bool):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": "invalid is_selected"})
        else:
            emailConfModel.is_selected = is_selected
            # Others is_selected inversion
            EmailConfModel.objects(id__ne=conf_id).update(is_selected=(not is_selected))

    # Only custom services，Is allowed to modify other fields
    if emailConfModel.is_default is False:
        # use_tls
        use_tls = form.use_tls
        if use_tls is not None:
            if not isinstance(use_tls, bool):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": "invalid use_tls"})
            else:
                emailConfModel.use_tls = use_tls
        # port
        port = form.port
        if port is not None:
            if (not isinstance(port, int)) or port <= 0:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": "invalid port"})
            else:
                emailConfModel.port = port

        # host
        host = form.host
        if host is not None:
            if not isinstance(host, str):
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": "invalid host"})
            else:
                emailConfModel.host = host

        # user
        user = form.user
        if user is not None:
            if not validate_email_format(user):
                print(f'Invalid email address: {user}')
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"Invalid email address [{user}]"})
            else:
                emailConfModel.user = user

        # password
        password = form.password
        if password is not None:
            # Decrypt the front-end encrypted password
            try:
                password = rsa_decrypt(form.password)
            except Exception as e:
                print(f'e: {e}')
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"msg": f"invalid password"})
            # Encrypted storage
            password_encrypted = sysconf_usecase.enc(password)
            emailConfModel.password_encrypted = password_encrypted

    # Update timestamp
    emailConfModel.updated_at = datetime.utcnow()
    emailConfModel.save()

    # Getting the data
    emailConfModel.reload()
    _data = convert_mongo_document_to_data(emailConfModel)
    data = dict()
    for field in EMAIL_CONF_KEYS:
        # FIXME： Encrypted transmission
        if field == 'password_encrypted':
            data['password'] = sysconf_usecase.dec(_data.get("password_encrypted")) if _data.get(
                "password_encrypted") not in (None, "") else ""
        else:
            data[field] = _data.get(field) or ''

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": jsonable_encoder(data)})


@router.get("/emailconfs/",
            summary="System mail configuration list")
def read_emailconfs(
        current_user: UserModel = Depends(deps.get_current_user)):

    # Determines if there is a built-in cas Mail service: If not，Then create a new
    emailConf_default = EmailConfModel.objects(is_default=True).first()
    if not emailConf_default:
        emailConf_default = EmailConfModel(
            id=generate_uuid(length=26),
            is_default=True,
            is_selected=True,
            name="Mail service"
        )
        emailConf_default.save()

    # Mail service：If not，Then create a new
    emailConf_custom = EmailConfModel.objects(is_default=False).first()
    if not emailConf_custom:
        emailConf_custom = EmailConfModel(
            id=generate_uuid(length=26),
            is_default=False,
            is_selected=False,
            name="Mail service",
            use_tls=True
        )
        emailConf_custom.save()

    #
    resp = []
    emailModels = EmailConfModel.objects.order_by("created_at").all()

    for emailModel in emailModels:
        data = convert_mongo_document_to_data(emailModel)
        #
        sub = dict()
        for field in EMAIL_CONF_KEYS:
            # FIXME： Encrypted transmission
            if field == 'password_encrypted':
                sub['password'] = sysconf_usecase.dec(data.get("password_encrypted")) if data.get("password_encrypted") not in (None, "") else ""
            else:
                sub[field] = data.get(field) or ''
        #
        resp.append(sub)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success",
                                 "data": jsonable_encoder(resp)})
