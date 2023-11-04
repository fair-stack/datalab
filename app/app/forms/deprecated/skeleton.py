from fastapi import Form, UploadFile, File


class SkeletonUpdateForm:
    def __init__(self,
                 version: str = Form(default=None),
                 version_meaning: str = Form(default=None),
                 name: str = Form(default=None),
                 description: str = Form(default=None),
                 introduction: str = Form(default=None),
                 logo: UploadFile = File(default=None),
                 ):
        self.version = version
        self.version_meaning = version_meaning
        self.name = name
        self.description = description
        self.introduction = introduction
        self.logo = logo


class SkeletonAdminUpdateForm:
    def __init__(self,
                 category: str = Form(default=None),
                 is_online: bool = Form(default=None),
                 ):
        self.category = category
        self.is_online = is_online
