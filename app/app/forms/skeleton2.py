from typing import List

from fastapi import Form, UploadFile, File


class Skeleton2UpdateForm:
    def __init__(self,
                 version: str = Form(default=None),
                 version_meaning: str = Form(default=None),
                 name: str = Form(default=None),
                 description: str = Form(default=None),
                 introduction: str = Form(default=None),
                 logo: UploadFile = File(default=None),
                 previews: List[UploadFile] = File(default=None),
                 organization: str = Form(default=None),
                 developer: str = Form(default=None),
                 contact_name: str = Form(default=None),
                 contact_email: str = Form(default=None),
                 contact_phone: str = Form(default=None),
                 statement: str = Form(default=None)
                 ):
        self.version = version
        self.version_meaning = version_meaning
        self.name = name
        self.description = description
        self.introduction = introduction
        self.logo = logo
        self.previews = previews
        self.organization = organization
        self.developer = developer
        self.contact_name = contact_name
        self.contact_email = contact_email
        self.contact_phone = contact_phone
        self.statement = statement


class Skeleton2AdminUpdateForm:
    def __init__(self,
                 category: str = Form(default=None),
                 is_online: bool = Form(default=None),
                 ):
        self.category = category
        self.is_online = is_online
