from fastapi import Form


class EmailConfUpdateForm:
    def __init__(self,
                 is_selected: bool = Form(None),
                 use_tls: bool = Form(None),
                 port: int = Form(None),
                 host: str = Form(None),
                 # user: EmailStr = Form(),
                 user: str = Form(None),        # Check for yourself
                 password: str = Form(None)
                 ):
        self.is_selected = is_selected
        self.use_tls = use_tls
        self.port = port
        self.host = host
        self.user = user
        self.password = password
