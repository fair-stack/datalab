# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:messages
@time:2022/11/16
"""

import datetime
from mongoengine import (
    StringField,
    BooleanField,
    Document,
    DateTimeField,
    ReferenceField,
    GenericReferenceField
)
from app.models.mongo import (
    UserModel,
    AuditRecordsModel,
    XmlToolSourceModel,
    StorageResourceAllocatedModel,
    ComputingResourceAllocatedModel,
)
from app.models.mongo.deprecated import (
    AnalysisModel,
    SkeletonModel,
)


class MessagesModel(Document):
    id = StringField(primary_key=True, required=True)
    user = ReferenceField(UserModel)
    from_user = ReferenceField(UserModel)
    title = StringField(required=True)
    content = StringField()
    messages_source = StringField(required=True)
    unread = BooleanField(required=True, default=True)
    creat_time = DateTimeField(default=datetime.datetime.utcnow())
    read_time = DateTimeField(default=datetime.datetime.utcnow())
    operation_type = BooleanField(default=False, required=True)
    operation = BooleanField(default=False, required=True)
    source = GenericReferenceField(choices=[AnalysisModel,
                                            SkeletonModel,
                                            XmlToolSourceModel,
                                            ComputingResourceAllocatedModel,
                                            StorageResourceAllocatedModel,
                                            AuditRecordsModel]
                                   )
    sub_level = StringField()
