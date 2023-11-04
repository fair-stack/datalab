from fastapi import Form, UploadFile, File


class UserCreateForm:
    def __init__(self,
                 name: str = Form(),
                 # email: EmailStr = Form(),
                 email: str = Form(),       # Check for yourself
                 organization: str = Form(),
                 password: str = Form()
                 ):
        self.name = name
        self.email = email
        self.organization = organization
        self.password = password


class UserUpdateForm:
    def __init__(self,
                 name: str = Form(default=None),
                 organization: str = Form(default=None),
                 password: str = Form(default=None),
                 avatar: UploadFile = File(default=None)
                 ):
        self.name = name
        self.organization = organization
        self.password = password
        self.avatar = avatar


class AdminUserUpdateForm:
    def __init__(self,
                 role: str = Form(default=None),
                 is_active: bool = Form(default=None)
                 ):
        self.role = role
        self.is_active = is_active
