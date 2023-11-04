# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:images
@time:2022/08/11
"""
from mongoengine import Document, IntField, StringField


class ImagesModel(Document):
    """
    """
    id = StringField(primary_key=True)
    image_id = StringField(required=True)
    image_short_id = StringField(required=True)
    source_id = StringField(required=True)
    source_name = StringField(required=True)
    tags = StringField(required=True)
    image_size = IntField()
    from_user = StringField(required=True)
    created_at = StringField(required=True)


class ComponentsImages(Document):
    image_from = StringField(primary_key=True)


if __name__ == '__main__':
    ...
