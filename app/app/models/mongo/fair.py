from mongoengine import (
    Document, StringField, IntField,
    ListField, EmbeddedDocument, BooleanField,
    EmbeddedDocumentField, DateTimeField, ReferenceField,GenericReferenceField,
    DictField,
)
from datetime import datetime
from app.models.mongo import UserModel, XmlToolSourceModel
from app.core.config import settings


class InstDbAuthorModel(EmbeddedDocument):
    name = StringField(required=True)
    email =StringField()


class InstDbModel(Document):
    id = StringField(required=True, primary_key=True)
    accessRights = StringField()
    sourceOrganizationLogo = StringField()
    sourceOrganizationName = StringField()
    datePublished = StringField()
    author = ListField(EmbeddedDocumentField(InstDbAuthorModel), default=list)
    description = StringField()
    ftp_user = StringField()
    ftp_password = StringField()
    ftp_ip = StringField()
    ftp_port = StringField()
    name_zh = StringField()
    name_en = StringField()
    data_size = StringField()


class FairMarketComponentsModel(Document):
    id = StringField(required=True, primary_key=True)
    bundle = StringField(required=True)
    CreateAt = DateTimeField(required=True)
    UpdateAt = DateTimeField(required=True)
    name = StringField(required=True)
    logo = StringField()
    description = StringField()
    category = StringField(required=True)
    size = IntField(required=True)
    authorName = StringField(required=True)
    softwareName = StringField()
    softwareLogo = StringField()
    publishStatus = IntField()
    enable = BooleanField(required=True, default=True)
    installed = BooleanField(required=True, default=False)
    installed_at = DateTimeField()
    installed_user = ReferenceField(UserModel)
    version = StringField()
    parameters = ListField()
    componentType = StringField(required=True, choices=settings.COMPONENT_TYPE)


class FairMarketComponentsTreeModel(Document):
    id = StringField(required=True, primary_key=True)
    category = StringField(required=True)
    counts = IntField(required=True, default=1)


class MarketComponentsInstallTaskModel(Document):
    id = StringField(required=True, primary_key=True)
    source = GenericReferenceField(choices=[
        FairMarketComponentsModel,
        XmlToolSourceModel
    ]
    )
    installed_user = ReferenceField(UserModel)
    installed_at = DateTimeField(default=datetime.utcnow)
    reinstall = BooleanField(required=True, default=False)
    reinstall_nums = IntField()
    status = StringField(required=True, default="PULL")
    source_type = StringField(required=True, default="NATIVE")


class VisualizationComponentModel(Document):
    id = StringField(required=True, primary_key=True)
    source = GenericReferenceField(choices=[FairMarketComponentsModel,
                                            XmlToolSourceModel], required=True)
    support = ListField()
    response_schema = ListField()
    create_at = DateTimeField(required=True)
    update_at = DateTimeField(required=True)
    name = StringField(required=True)
    enable = BooleanField(required=True, default=True)
    used_counts = IntField(default=0)
