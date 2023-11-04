# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:images
@time:2022/08/11
"""
import os
import uuid
import shutil
import pymongo
from dataclasses import dataclass
from app.utils.docker_util.dockerfile_generator import DockerFileGenerator
from app.utils.docker_util.executor import ContainerManger
from app.core.config import settings


def parcel_pip(_req: dict):
    if _req.get('version') is None:
        return _req['value']
    return f"{_req['value']}=={_req['version']}"


def parcel_language(_req: dict, language_map: dict):
    if _req['type'] == "language":
        language = language_map.get(_req['value'])
        assert language is not None
        _tag_name = language.get(_req['version'])
        if _tag_name is not None:
            return _tag_name
        else:
            # TODO Handle no environment version plan to be determined
            ...


@dataclass
class PythonImages:
    """XMLMetadata  XML_Source.dict()"""
    xml_source: dict
    "Build directories Prohibited use tmpfileBuilding a temporary directory，Causes a remote creation read/write exception."
    root_dir: str
    """The base environment image map is then augmented, Temporary writing death
    language_map_image = {
    'R': {"3.6.0": "r:3.6.0", "1": "componentrpy"},
    "python": {"3.9.0": "python3.9:v2", "3.9": "componentrpy"},
                          }
    """
    language_map_image: dict

    @property
    def parse_requirements(self):
        return "\n".join([parcel_pip(_) for _ in self.xml_source['requirements'] if _['type'] == 'package'])

    def to_requirements(self, path):
        requirements_list = self.parse_requirements
        with open(os.path.join(path, 'requirements.txt'), 'w') as f:
            f.write(requirements_list)

    @property
    def parse_language(self):
        _language_list = [parcel_language(_, self.language_map_image) for _ in self.xml_source['requirements'] if
                          _['type'] == 'language']
        return 'component:v1'

    @property
    def project_name(self):
        return self.xml_source['folder_path'].rsplit('/', maxsplit=1)[-1]

    def generator(self, tag: str):
        tmp_dir = os.path.join(self.root_dir, uuid.uuid4().__str__())
        os.mkdir(tmp_dir)
        dockerfile_output_path = os.path.join(tmp_dir, 'Dockerfile')
        self.to_requirements(self.xml_source['folder_path'])
        dfg = DockerFileGenerator()
        dfg.images_from(tag=self.parse_language)
        dfg.images_maintainer(self.xml_source['author'])
        _project_name = self.project_name
        dfg.images_copy(_project_name, f'/home/{_project_name}')
        dfg.images_run(f"pip install -r /home/{_project_name}/requirements.txt")
        dfg.images_env(LC_ALL="zh_CN.UTF-8")
        shutil.copytree(self.xml_source['folder_path'], tmp_dir + f'/{_project_name}')
        dfg.output(dockerfile_output_path)
        cli = ContainerManger()
        build_info = cli.build_image(path=tmp_dir, tag=tag)
        _image = build_info[0]
        shutil.rmtree(tmp_dir, ignore_errors=True)
        # image_model_ins = dict()
        # image_model_ins['id'] = uuid.uuid4().__str__()
        # image_model_ins['image_id'] = _image.id
        # image_model_ins['image_short_id'] = _image.short_id
        # image_model_ins['source_id'] = self.xml_source['_id']
        # image_model_ins['source_name'] = self.xml_source['name']
        # image_model_ins['tags'] = tag
        # image_model_ins['image_size'] = _image.attrs['Size']
        # image_model_ins['from_user'] = self.xml_source['user']
        # image_model_ins['created_at'] = _image.attrs['Created']
        # pymongo.MongoClient(settings.MONGODB_SERVER)[settings.MONGODB_DB]['images_model'].insert_one(image_model_ins)
        return build_info
