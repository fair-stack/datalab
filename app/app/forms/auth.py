from fastapi import Form


class PasswordForgetForm:
    def __init__(self,
                 username: str = Form(),
                 # email: EmailStr = Form(),
                 email: str = Form(),   # Check for yourself
                 ):
        self.username = username
        self.email = email


class PasswordResetForm:
    def __init__(self,
                 token: str = Form(),
                 password: str = Form()
                 ):
        self.token = token
        self.password = password
