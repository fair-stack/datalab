# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:msg_util
@time:2022/11/10
"""
ADMIN_CODE = "L1-03"
AUDIT_CODE = ["L3-07", "L3-12", "L3-15"]
RECORDS_ROLE_MAP = {"L3-07": "Tool audit", "L3-12": "Resources", "L3-15": "Component auditing"}
from app.models.mongo import (
    UserModel,
    MessagesModel,
    XmlToolSourceModel,
    ComputingResourceAllocatedModel,
    StorageResourceAllocatedModel,
    AuditRecordsModel
)
from app.models.mongo.deprecated import AnalysisModel,SkeletonModel

from app.utils.common import generate_uuid
from typing import Optional, Union


def find_records(permissions: list):
    audit_info_permissions = list()
    print(permissions)

    def inner(x: list):
        for c in x:
            if c['code'] in AUDIT_CODE:
                if c['checked']:
                    audit_info_permissions.append(RECORDS_ROLE_MAP.get(c['code']))
            else:
                if c['children']:
                    inner(c['children'])
    for _ in filter(lambda x: x if x['code'] == ADMIN_CODE else None, permissions):
        inner(_['children'])
    if "Resources" in audit_info_permissions:
        audit_info_permissions.remove("Resources")
        audit_info_permissions.extend(["Resources", "Resources"])
    return audit_info_permissions


class MessageBase:
    state_text = None

    def __init__(self,
                 user: UserModel,
                 messages_source: str,
                 source_model: [AnalysisModel, SkeletonModel, XmlToolSourceModel, ComputingResourceAllocatedModel,
                                StorageResourceAllocatedModel, AuditRecordsModel],
                 content: Optional[str],
                 sub_level: Optional[str] = None):
        self.content = content
        self.user = user
        self.source_model = source_model
        self.messages_source = messages_source
        self.sub_level = sub_level


    def create_title(self):
        raise NotImplementedError

    def create_content(self):
        raise NotImplementedError

    def create(self, operation_type: bool = False):
        title = self.create_title()
        content = self.content if self.content is not None else self.create_content()
        MessagesModel(id=generate_uuid(),
                      user=self.user,
                      title=title,
                      content=content,
                      messages_source=self.messages_source,
                      source=self.source_model,
                      sub_level=self.sub_level,
                      operation_type= operation_type
                      ).save()


class AnalysisMessage(MessageBase):
    def create_content(self):
        return f"Analysis tasks<{self.source_model.name}> Start time: {self.source_model.created_at}, " \
               f"{'End time:'  if self.source_model.state == 'COMPLETED' else 'Time to failure:'} {self.source_model.updated_at}"

    def create_title(self):
        return f"{self.user}Hello.，Analysis tasks{'To complete with execution' if self.source_model.state == 'COMPLETED' else 'Execution failure'}"


class SkeletonForUserMessage(MessageBase):
    def create_content(self):
        return f"Your publishing tool application{self.state_text},Please go to the Personal Center tool to apply for this information."

    def create_title(self):
        if self.source_model.audit_result == 'Approved by review':
            self.state_text = 'Approved by review'
        elif self.source_model.audit_result == 'Failed to pass the audit':
            self.state_text = 'Has been rejected.'
        return f"Your publishing tool application{self.state_text}!"


class SkeletonForAdminMessage(MessageBase):
    def create_content(self):
        return f"{self.user.name}<{self.user.email}>A release tool application was submitted，Tools：{self.source_model.component.name}, " \
               f"Version：{self.source_model.component.version}," \
               f"Information：{self.source_model.component.introduction}"

    def create_title(self):
        return f"Hello.，Users{self.user.name}<{self.user.email}>Tools，Please go to review!"


class XmlToolSourceForAdminMessage(MessageBase):
    def create_content(self):
        return f"{self.user.name}<{self.user.email}>A release component request was submitted，Components：{self.source_model.name}" \
               f"Version：{self.source_model.version}," \
               f"Classification：{self.source_model.category}"

    def create_title(self):
        return f"Hello.，Users{self.user.name}<{self.user.email}>Components，Please go to review!"


class XmlToolSourceForUserMessage(MessageBase):
    def create_content(self):
        return f"Components{self.state_text},ComponentsInformation"

    def create_title(self):
        if self.source_model.audit_result == 'Approved by review':
            self.state_text = 'Approved by review'
        elif self.source_model.audit_result == 'Failed to pass the audit':
            self.state_text = 'Has been rejected.'
        return f"Your publishing tool application{self.state_text}!"


class ComputingResourceAllocatedForAdminMessage(MessageBase):
    def create_content(self):
        return f"{self.user.name}<{self.user.email}>Resources，Resources：{self.source_model.component.name}"\
               f"Application amount：{self.source_model.apply_nums}," \
               f"Information：{self.source_model.content}"

    def create_title(self):
        return f"Hello.，Users{self.user.name}<{self.user.email}>Resources，Please go to review!"


class ComputingResourceAllocatedForUserMessage(MessageBase):
    def create_content(self):
        return f"Resources{self.state_text},ResourcesInformation"

    def create_title(self):
        if self.source_model.audit_result == 'Approved by review':
            self.state_text = 'Approved by review'
        elif self.source_model.audit_result == 'Failed to pass the audit':
            self.state_text = 'Has been rejected.'
        return f"Resources{self.state_text}!"


class StorageResourceAllocatedForAdminMessage(MessageBase):
    def create_content(self):
        print(self.source_model.component)
        return f"{self.user.name}<{self.user.email}>Resources，Resources：Users" \
               f"Application amount：{self.source_model.apply_nums}," \
               f"Information：{self.source_model.content}"

    def create_title(self):
        return f"Hello.，Users{self.user.name}<{self.user.email}>Resources，Please go to review!"


class StorageResourceAllocatedForUserMessage(MessageBase):
    def create_content(self):
        return f"Resources{self.state_text},ResourcesInformation"

    def create_title(self):
        if self.source_model.audit_result == 'Approved by review':
            self.state_text = 'Approved by review'
        elif self.source_model.audit_result == 'Failed to pass the audit':
            self.state_text = 'Has been rejected.'
        return f"Resources{self.state_text}!"


class MessagesContext:
    def __init__(self, message_instance):
        self.message_instance = message_instance

    def create(self, operation_type):
        return self.message_instance.create(operation_type)


def creat_message(user: UserModel, message_base, content: Optional[str] = None, for_user=False):
    """
    user： Users
    message_base: Correspond to an entity，Tools，message_baseYou should write for AuditRecordsModel， After the administrator's approval message_baseYou should write forToolsModel
    """

    if isinstance(message_base, AnalysisModel):
        return MessagesContext(AnalysisMessage(user=user, messages_source="Analysis tasks", source_model=message_base,
                                               content=content)).create()
    elif isinstance(message_base, SkeletonModel):
        return MessagesContext(SkeletonForUserMessage(user=user, messages_source="Tools", source_model=message_base,
                                                      content=content)).create()
    elif isinstance(message_base, XmlToolSourceModel):
        return MessagesContext(XmlToolSourceForUserMessage(user=user, messages_source="Components", source_model=message_base,
                                                           content=content)).create()
    elif isinstance(message_base, AuditRecordsModel):
        print(message_base, for_user)
        if for_user:
            if message_base.audit_type == "Resources":
                return MessagesContext(ComputingResourceAllocatedForUserMessage(user=user, messages_source="Resources",
                                                                            source_model=message_base, content=content)
                                   ).create(False)
            elif message_base.audit_type == 'Resources':
                return MessagesContext(StorageResourceAllocatedForUserMessage(user=user, messages_source="Resources",
                                                                                source_model=message_base,
                                                                                content=content)
                                       ).create(False)
            elif message_base.audit_type == "Tools":
                return MessagesContext(SkeletonForUserMessage(user=user, messages_source="Tools",
                                                              source_model=message_base,
                                                              content=content)).create(False)
        else:
            if message_base.audit_type == "Resources":
                return MessagesContext(ComputingResourceAllocatedForAdminMessage(user=user, messages_source="Resources",
                                                                                 source_model=message_base,
                                                                                 content=content,
                                                                                 sub_level="Resources")).create(True)
            elif message_base.audit_type == "Resources":
                return MessagesContext(StorageResourceAllocatedForAdminMessage(user=user, messages_source="Resources",
                                                                               source_model=message_base,
                                                                               content=content,
                                                                               sub_level="Resources")).create(True)
            elif message_base.audit_type == 'Components':
                return MessagesContext(XmlToolSourceForAdminMessage(user=user, messages_source="Component auditing",
                                                                    source_model=message_base,
                                                                    content=content,
                                                                    sub_level="Components")).create(True)
            elif message_base.audit_type == 'Tools':
                return MessagesContext(SkeletonForAdminMessage(user=user, messages_source="Tool audit",
                                                               source_model=message_base,
                                                               content=content,
                                                               sub_level="Tools")).create(True)
    else:
        raise TypeError("Unknown event type")


# {
#     "userName": string,          // Account number
#     "softwareId": "63b7fc6e94de2e92484b2363",
#     "softwareName": "DataLab",
#     "softwareVersion": string,   // Version
#     "softwareData": {            // Software data
#         "AnalysisToolsCount": int,   // Resources
#         "ExperimentCount": int,      // Number of experiments
#         "InteractiveProgrammingCount": int,    // Number of interactive programming items
#         "ComponentCount": int,     // Components
#         "Cores": int,       // Number of cores
#         "UsersCount": int        // Users
#         "Memory": int    // Memory size
#         "PublicData": int        // Open data
#     }
# }
