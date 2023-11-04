import smtplib
import ssl
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import EmailStr
from typing import List

from app.core.config import settings
from app.core.jwt import create_email_verify_token
from app.models.mongo import EmailConfModel
from app.usecases import sysconf_usecase


def validate_email_format(email: str) -> bool:
    try:
        if EmailStr.validate(email):
            return True
        else:
            print(f'invalid email address: {email}')
            return False
    except Exception as e:
        print(f'e: {e}')
        return False


def send_email_via_default_smtp_server(to_addrs: List[str], msg: MIMEMultipart):
    emailConf = EmailConfModel.objects(is_default=False, is_selected=True).first()
    if emailConf is not None:
        SMTP_TLS = emailConf.use_tls
        SMTP_PORT = emailConf.port
        SMTP_HOST = emailConf.host
        SMTP_USER = emailConf.user
        SMTP_PASSWORD = sysconf_usecase.dec(emailConf.password_encrypted)
    else:
        SMTP_TLS = settings.SMTP_TLS
        SMTP_PORT = settings.SMTP_PORT
        SMTP_HOST = settings.SMTP_HOST
        SMTP_USER = settings.SMTP_USER
        SMTP_PASSWORD = settings.SMTP_PASSWORD
    # Determining whether to use TLS
    if SMTP_TLS is True:
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(host=SMTP_HOST, port=SMTP_PORT, context=context)
    else:
        server = smtplib.SMTP(host=SMTP_HOST, port=SMTP_PORT)
    #
    server.login(user=SMTP_USER, password=SMTP_PASSWORD)
    server.sendmail(from_addr=SMTP_USER, to_addrs=to_addrs, msg=msg.as_string())
    server.close()


if __name__ == "__main__":
    email = 'test2@example.com'
    token = create_email_verify_token(data={"email": email})

    msg = MIMEMultipart()
    msg['Subject'] = Header('DataLab Email verification', 'utf-8')
    # msg['From'] = Header(settings.SMTP_USER)
    msg['From'] = Header("kungreye@sina.com")

    html = f"""\
    <html>
      <body>
        <p>Salute! This is DataLab. 
        <br/>
        <br/>
           <a href="http://127.0.0.1:8000/api/emailVerify?token={token}">Click to verify your email address.</a> 
        </p>
      </body>
    </html>
    """
    part1 = MIMEText(html, 'html')
    msg.attach(part1)

    receivers = ['jlduan@cnic.cn']
    send_email_via_default_smtp_server(to_addrs=receivers, msg=msg)
