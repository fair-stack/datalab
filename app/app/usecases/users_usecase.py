from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from typing import Dict, Tuple, Optional

import aioredis
from fastapi import status

from app.core.config import settings
from app.core.jwt import create_email_verify_token, create_password_reset_token
from app.core.security import get_password_hash
from app.crud import crud_user
from app.forms import UserCreateForm
from app.models.mongo import IndexUiModel, UserModel
from app.schemas import UserInDBSchema
from app.usecases import ui_usecase, roles_usecase
from app.utils.common import generate_uuid, convert_mongo_document_to_data
from app.utils.email_util import send_email_via_default_smtp_server, validate_email_format
from app.utils.file_util import get_img_b64_stream
from app.utils.safety_util import rsa_decrypt, check_password_strength


@lru_cache(maxsize=1)
def get_copyright():
    copyright = "copyright"
    indexui = IndexUiModel.objects.first()
    if indexui:
        styles_copyright = indexui.styles_copyright
        if isinstance(styles_copyright, dict):
            copyright = styles_copyright.get("copyright", "copyright")
    return copyright


def filter_out_user_sensitive_field(data: dict):
    # Remove sensitive fields
    for field in ['from_source', 'hashed_password', 'is_email_verified', 'is_superuser']:
        data.pop(field, None)
    return data


def create_user(form: UserCreateForm) -> Tuple:
    """
    Create new user.
    """

    # Verify that the email format is valid
    if not validate_email_format(form.email):
        code = status.HTTP_400_BAD_REQUEST
        msg = f"Invalid email address [{form.email}]"
        return code, msg

    # Determines if the user exists
    user = crud_user.get_user_by_email(form.email)
    # The user does not exist
    if not user:
        # Decrypt the front-end encrypted password
        try:
            password = rsa_decrypt(form.password) if form.password is not None else None
        except Exception as e:
            print(f'e: {e}')
            code = status.HTTP_400_BAD_REQUEST
            msg = f"invalid password"
            return code, msg

        # Verify password strength
        code, msg, _ = check_password_strength(password)
        if code != status.HTTP_200_OK:
            return code, msg

        # Preset roles
        roles_usecase.init_roles_innate()
        # Creating roles
        user = crud_user.create_user_via_form(form)
        if user:
            code = status.HTTP_200_OK
            msg = "success"
        else:
            code = status.HTTP_500_INTERNAL_SERVER_ERROR
            msg = "Registration error，Please try again later"
    else:
        code = status.HTTP_400_BAD_REQUEST
        msg = f"Users [{form.email}] Already exist，Non-repeatable registration"

    return code, msg


async def read_user(user_id: str) -> Tuple[int, str, Optional[Dict]]:
    """

    :param user_id:
    :return:
    """
    code = status.HTTP_200_OK
    msg = "success"
    data = None

    user = UserModel.objects(id=user_id).first()
    if user is None:
        code = status.HTTP_404_NOT_FOUND
        msg = f"user not found for {user_id}"
        return code, msg, data

    data = convert_mongo_document_to_data(user)
    # if data.get("avatar") is not None:
    #     data['avatar'] = get_img_b64_stream(data.get("avatar"))
    # else:
    #     data['avatar'] = ''


    # Remove sensitive fields
    data = filter_out_user_sensitive_field(data)

    return code, msg, data


def send_email_verification_email_in_signup(username: str, to_addr: str):
    """
    Users，To verify the validity of the mailbox
    :param username:
    :param to_addr:
    :return:
    """
    platform_data = ui_usecase.read_platform()
    if platform_data is None:
        platform_name = "DataLab"
    else:
        platform_name = platform_data.get("name", "DataLab")

    token = create_email_verify_token(data={"username": username, "email": to_addr})

    msg = MIMEMultipart()
    msg['Subject'] = Header('Email verification', 'utf-8')
    msg['From'] = Header(settings.SMTP_USER)

    html = '''
<!DOCTYPE html>
<html">
<head>
    <style class="fox_global_style">
        div.fox_html_content {{ line-height: 1.5;}}
        /* Some default styles */
        blockquote {{ margin-Top: 0px; margin-Bottom: 0px; margin-Left: 0.5em }}
        ol, ul {{ margin-Top: 0px; margin-Bottom: 0px; list-style-position: inside; }}
        p {{ margin-Top: 0px; margin-Bottom: 0px }}
    </style>
</head>
<body>
<table class="body" width="100%" bgcolor="#f1f1f1" style="color: rgb(0, 0, 0); font-size: 14px; line-height: 23.8px; font-family: &quot;lucida Grande&quot;, Verdana; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
    <tbody>
    <tr>
        <td class="body" align="center" valign="top" width="100%" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
            <center>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" bgcolor="#f1f1f1" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                                <tbody>
                                <tr height="50">
                                    <td width="100%" height="50" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>


                                </tbody>
                            </table>
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="560" class="panel-padded" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 560px;">
                                            <tbody>
                                            <tr>
                                                <td width="560" align="center" style="font-family: arial, helvetica, sans-serif; font-size: 30px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; font-weight: bold; color: rgb(49, 49, 49); line-height: 75px;">
                                                    <div style="line-height: 75px;">{org}

                                                    </div></td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" bgcolor="#f1f1f1" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" bgcolor="#ffffff" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="560" class="panel-padded" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 560px;">
                                            <tbody>

                                            <tr>
                                                <td width="560" align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 24px;">
                                                    <div style="line-height: 24px;">
                                                        <br />
                                                    </div>
                                                    <div style="line-height: 24px;">
                                                        <br />
                                                        <span style="color: rgb(49, 49, 49); font-family: arial, helvetica, sans-serif; font-size: 35px; font-weight: 700;">
                                                            Pending Activation notification!</span>
                                                        <br />
                                                        <br />
                                                    </div></td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="540" border="0" cellspacing="0" cellpadding="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                            <tbody>
                                            <tr>
                                                <td style="font-family: arial, helvetica, sans-serif; font-size: 14px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; text-transform: uppercase; color: rgb(178, 178, 178); line-height: 24px;"><strong>Notice Details:</strong></td>
                                            </tr>
                                            <tr height="1">
                                                <td width="100%" height="1" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px; background-color: rgb(226, 227, 228);">&nbsp;</td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr height="15">
                                    <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="540" border="0" cellspacing="0" cellpadding="0" style="text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                            <tbody>
                                            <tr>
                                                <td style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                    <table align="left" border="0" cellpadding="0" cellspacing="0" width="270" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 270px;">
                                                        <tbody>
                                                        <tr>
                                                            <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                                <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 16px; color: rgb(49, 49, 49); text-align: left; line-height: 24px;">
                        <span style="font-weight: 700;"><br />
                         <div class="greeting">
                         <h2>{username} Hello.! Welcome to join us {org}</h2>
                              <br />
                         </div>
                           <span style="font-weight: normal;">Your account Number {email} The application has been successful.!</span>
                                 <br /><span style="font-weight: normal;"  >To keep your account safe，We need to make sure that you are the owner of this email account. Please click the button below，To activate and confirm your email address！</span>
                        </span>
                                                                </div>
                                                                <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 16px; color: rgb(49, 49, 49); text-align: left; line-height: 24px;">
                                                                    <div class="gen-txt" style="color: rgb(0, 0, 0); font-family: Verdana; font-size: medium; width: 438px;">
                                                                        <div style="width: 438px;">
                                                                            <table width="100%" cellpadding="0" cellspacing="0" border="0" align="left" style="padding-top: 7px; padding-bottom: 15px;">
                                                                                <tbody>
                                                                                <tr>
                                                                                    <td style="font-family: &quot;lucida Grande&quot;, Verdana; font-size: 12px; -webkit-font-smoothing: subpixel-antialiased;">
                                                                                        <table class="blue-button" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(rgb(59, 156, 232) 0%, rgb(1, 113, 201) 100%) left top repeat-x; border-radius: 8px; border: 0px; margin-top: 20px; text-align: center; padding-top: 3px; padding-bottom: 4px;">
                                                                                            <tbody>
                                                                                            <tr>
                                                                                                <td align="center" valign="middle" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased;"><a href="{url}" target="_blank" rel="noopener" style="text-decoration-line: none; outline: none; cursor: pointer; line-height: 26px; padding: 0px 50px; display: block; color: rgb(255, 255, 255) !important;">activation</a></td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table><br /></td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                        </div>
                                                                    </div>
                                                                    <div class="gen-txt" style="color: rgb(0, 0, 0); font-family: Verdana; font-size: medium; width: 438px;">
                                                                        <div style="padding-top: 12px; width: 438px;">
                                                                            <br />
                                                                        </div>
                                                                    </div>
                                                                    <div class="gen-txt" style="color: rgb(0, 0, 0); font-family: Verdana; font-size: medium; width: 438px;">
                                                                        <div class="gen-txt" style="width: 438px; padding-top: 12px;">
                                                                            Links don't work？Please copy the following address into your browser's address baractivation
                                                                        </div>
                                                                        <div class="gen-txt" style="width: 438px; padding-top: 12px;">
                                                                            <span style="color: rgb(153, 153, 153);"><a href="{url}"  rel="noopener" target="_blank" style="outline: none; cursor: pointer; color: rgb(8, 42, 78); text-decoration-line: none !important;"> <span>{url}</span></a></span>
                                                                        </div>
                                                                    </div>
                                                                </div></td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                    <table align="right" border="0" cellpadding="0" cellspacing="0" width="270" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 270px;">
                                                        <tbody>
                                                        <tr>
                                                            <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                                <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 16px; color: rgb(49, 49, 49); text-align: left; line-height: 24px;">
                                                                    <br />
                                                                </div></td>
                                                        </tr>
                                                        <tr height="1" class="desktop-hide" style="height: 0px;">
                                                            <td width="100%" height="1" class="desktop-hide" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; height: 0px; line-height: 1px;">&nbsp;</td>
                                                        </tr>
                                                        </tbody>
                                                    </table></td>
                                            </tr>
                                            <tr height="15">
                                                <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr height="15">
                                    <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="540" border="0" cellspacing="0" cellpadding="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                            <tbody>
                                            <tr height="1">
                                                <td width="100%" height="1" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px; background-color: rgb(226, 227, 228);">&nbsp;</td>
                                            </tr>
                                            <tr height="20">
                                                <td width="100%" height="20" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                            </tr>
                                            <tr>
                                                <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                    <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 14px; color: rgb(49, 49, 49); line-height: 26px; width: 540px;">
                                                        Please visit the24activation，Otherwise, this validation will fail，You will need to re-register the CAPTCHA.
                                                    </div>
                                                    <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 14px; color: rgb(49, 49, 49); line-height: 26px; width: 540px;"></div></td>
                                            </tr>
                                            <tr height="50">
                                                <td width="100%" height="50" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;"><br /><br />&nbsp;</td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" class="panel" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                                <tbody>
                                <tr height="15">
                                    <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="560" class="panel" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 560px;">
                                            <tbody>
                                            <tr>
                                                <td align="center" class="panel-padded" style="font-size: 10px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; color: rgb(49, 49, 49);">
                                                    <p style="line-height: 20.4px; margin-right: 0px !important; margin-left: 0px !important;">{copyright}
                                                    </p></td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
            </center></td>
    </tr>
    </tbody>
</table>
</body>
</html>
'''.format(
        homeUrl=f"http://{settings.SERVER_HOST}/index",
        image='',
        username=username,
        org=platform_name,
        email=to_addr,
        url=f"http://{settings.SERVER_HOST}/api/emailVerify?token={token}",
        copyright=get_copyright()
    )
    part = MIMEText(html, 'html')
    msg.attach(part)

    to_addrs = [to_addr]
    send_email_via_default_smtp_server(to_addrs=to_addrs, msg=msg)


def send_password_reset_email(username: str, to_addr: str):
    """
    When you forget your password，Send a password reset email
    :param username:
    :param to_addr:
    :return:
    """
    platform_data = ui_usecase.read_platform()
    if platform_data is None:
        platform_name = "DataLab"
    else:
        platform_name = platform_data.get("name", "DataLab")

    token = create_password_reset_token(data={"username": username, "email": to_addr})

    msg = MIMEMultipart()
    msg['Subject'] = Header('Password reset', 'utf-8')
    msg['From'] = Header(settings.SMTP_USER)

    html = '''
<!DOCTYPE html>
<html">
<head>
    <style class="fox_global_style">
        div.fox_html_content {{ line-height: 1.5;}}
        /* Some default styles */
        blockquote {{ margin-Top: 0px; margin-Bottom: 0px; margin-Left: 0.5em }}
        ol, ul {{ margin-Top: 0px; margin-Bottom: 0px; list-style-position: inside; }}
        p {{ margin-Top: 0px; margin-Bottom: 0px }}
    </style>
</head>
<body>
<table class="body" width="100%" bgcolor="#f1f1f1" style="color: rgb(0, 0, 0); font-size: 14px; line-height: 23.8px; font-family: &quot;lucida Grande&quot;, Verdana; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
    <tbody>
    <tr>
        <td class="body" align="center" valign="top" width="100%" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
            <center>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" bgcolor="#f1f1f1" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                                <tbody>
                                <tr height="50">
                                    <td width="100%" height="50" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>


                                </tbody>
                            </table>
                            <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="560" class="panel-padded" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 560px;">
                                            <tbody>
                                            <tr>
                                                <td width="560" align="center" style="font-family: arial, helvetica, sans-serif; font-size: 30px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; font-weight: bold; color: rgb(49, 49, 49); line-height: 75px;">
                                                    <div style="line-height: 75px;">{org}

                                                    </div></td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" bgcolor="#f1f1f1" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" bgcolor="#ffffff" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="560" class="panel-padded" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 560px;">
                                            <tbody>

                                            <tr>
                                                <td width="560" align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 24px;">
                                                    <div style="line-height: 24px;">
                                                        <br />
                                                    </div>
                                                    <div style="line-height: 24px;">
                                                        <br />
                                                        <span style="color: rgb(49, 49, 49); font-family: arial, helvetica, sans-serif; font-size: 35px; font-weight: 700;">
                                                            Password reset</span>
                                                        <br />
                                                        <br />
                                                    </div></td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="540" border="0" cellspacing="0" cellpadding="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                            <tbody>
                                            <tr>
                                                <td style="font-family: arial, helvetica, sans-serif; font-size: 14px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; text-transform: uppercase; color: rgb(178, 178, 178); line-height: 24px;"><strong>Details:</strong></td>
                                            </tr>
                                            <tr height="1">
                                                <td width="100%" height="1" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px; background-color: rgb(226, 227, 228);">&nbsp;</td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr height="15">
                                    <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="540" border="0" cellspacing="0" cellpadding="0" style="text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                            <tbody>
                                            <tr>
                                                <td style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                    <table align="left" border="0" cellpadding="0" cellspacing="0" width="270" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 270px;">
                                                        <tbody>
                                                        <tr>
                                                            <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                                <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 16px; color: rgb(49, 49, 49); text-align: left; line-height: 24px;">
                        <span style="font-weight: 700;"><br />
                         <div class="greeting">
                         <h2>Hello.! {username}.</h2>
                              <br />
                         </div>
                                <span style="font-weight: normal;">Please click the button below，Reset login password！</span>
                        </span>
                                                                </div>
                                                                <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 16px; color: rgb(49, 49, 49); text-align: left; line-height: 24px;">
                                                                    <div class="gen-txt" style="color: rgb(0, 0, 0); font-family: Verdana; font-size: medium; width: 438px;">
                                                                        <div style="width: 438px;">
                                                                            <table width="100%" cellpadding="0" cellspacing="0" border="0" align="left" style="padding-top: 7px; padding-bottom: 15px;">
                                                                                <tbody>
                                                                                <tr>
                                                                                    <td style="font-family: &quot;lucida Grande&quot;, Verdana; font-size: 12px; -webkit-font-smoothing: subpixel-antialiased;">
                                                                                        <table class="blue-button" cellpadding="0" cellspacing="0" border="0" style="background: linear-gradient(rgb(59, 156, 232) 0%, rgb(1, 113, 201) 100%) left top repeat-x; border-radius: 8px; border: 0px; margin-top: 20px; text-align: center; padding-top: 3px; padding-bottom: 4px;">
                                                                                            <tbody>
                                                                                            <tr>
                                                                                                <td align="center" valign="middle" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased;"><a href="{url}" target="_blank" rel="noopener" style="text-decoration-line: none; outline: none; cursor: pointer; line-height: 26px; padding: 0px 50px; display: block; color: rgb(255, 255, 255) !important;">Reset</a></td>
                                                                                            </tr>
                                                                                            </tbody>
                                                                                        </table><br /></td>
                                                                                </tr>
                                                                                </tbody>
                                                                            </table>
                                                                        </div>
                                                                    </div>
                                                                    <div class="gen-txt" style="color: rgb(0, 0, 0); font-family: Verdana; font-size: medium; width: 438px;">
                                                                        <div style="padding-top: 12px; width: 438px;">
                                                                            <br />
                                                                        </div>
                                                                    </div>
                                                                    <div class="gen-txt" style="color: rgb(0, 0, 0); font-family: Verdana; font-size: medium; width: 438px;">
                                                                        <div class="gen-txt" style="width: 438px; padding-top: 12px;">
                                                                            Links don't work？Please copy the following address into your browser's address bar
                                                                        </div>
                                                                        <div class="gen-txt" style="width: 438px; padding-top: 12px;">
                                                                            <span style="color: rgb(153, 153, 153);"><a href="{url}"  rel="noopener" target="_blank" style="outline: none; cursor: pointer; color: rgb(8, 42, 78); text-decoration-line: none !important;"> <span>{url}</span></a></span>
                                                                        </div>
                                                                    </div>
                                                                </div></td>
                                                        </tr>
                                                        </tbody>
                                                    </table>
                                                    <table align="right" border="0" cellpadding="0" cellspacing="0" width="270" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 270px;">
                                                        <tbody>
                                                        <tr>
                                                            <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                                <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 16px; color: rgb(49, 49, 49); text-align: left; line-height: 24px;">
                                                                    <br />
                                                                </div></td>
                                                        </tr>
                                                        <tr height="1" class="desktop-hide" style="height: 0px;">
                                                            <td width="100%" height="1" class="desktop-hide" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; height: 0px; line-height: 1px;">&nbsp;</td>
                                                        </tr>
                                                        </tbody>
                                                    </table></td>
                                            </tr>
                                            <tr height="15">
                                                <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr height="15">
                                    <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" class="body" style="line-height: 20.4px; text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" border="0" cellpadding="0" cellspacing="0" bgcolor="#ffffff" class="panel" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px; background-color: rgb(255, 255, 255);">
                                <tbody>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="540" border="0" cellspacing="0" cellpadding="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                            <tbody>
                                            <tr height="1">
                                                <td width="100%" height="1" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px; background-color: rgb(226, 227, 228);">&nbsp;</td>
                                            </tr>
                                            <tr height="20">
                                                <td width="100%" height="20" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                            </tr>
                                            <tr>
                                                <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                                    <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 14px; color: rgb(49, 49, 49); line-height: 26px; width: 540px;">
                                                        Please visit the1Operation completed within hours，Otherwise this link will be broken.
                                                    </div>
                                                    <div style="font-family: Ariel, Helvetica, sans-serif; font-size: 14px; color: rgb(49, 49, 49); line-height: 26px; width: 540px;"></div></td>
                                            </tr>
                                            <tr height="50">
                                                <td width="100%" height="50" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;"><br /><br />&nbsp;</td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="text-align: center; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                    <tbody>
                    <tr>
                        <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                            <table width="600" class="panel" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 600px;">
                                <tbody>
                                <tr height="15">
                                    <td width="100%" height="15" style="font-size: 1px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; line-height: 1px;">&nbsp;</td>
                                </tr>
                                <tr>
                                    <td align="center" style="font-size: 12px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse;">
                                        <table width="560" class="panel" border="0" cellpadding="0" cellspacing="0" style="text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; min-width: 560px;">
                                            <tbody>
                                            <tr>
                                                <td align="center" class="panel-padded" style="font-size: 10px; -webkit-font-smoothing: subpixel-antialiased; text-size-adjust: 100%; margin: 0px; padding: 0px; border-collapse: collapse; color: rgb(49, 49, 49);">
                                                    <p style="line-height: 20.4px; margin-right: 0px !important; margin-left: 0px !important;">{copyright}
                                                    </p></td>
                                            </tr>
                                            </tbody>
                                        </table></td>
                                </tr>
                                </tbody>
                            </table></td>
                    </tr>
                    </tbody>
                </table>
            </center></td>
    </tr>
    </tbody>
</table>
</body>
</html>
'''.format(
        homeUrl=f"http://{settings.SERVER_HOST}/index",
        image='',
        org=platform_name,
        email=to_addr,
        username=username,
        url=f"http://{settings.SERVER_HOST}/resetPsd?token={token}",
        copyright=get_copyright()
    )
    part = MIMEText(html, 'html')
    msg.attach(part)

    to_addrs = [to_addr]
    send_email_via_default_smtp_server(to_addrs=to_addrs, msg=msg)
