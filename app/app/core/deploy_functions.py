# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:deploy_functions
@time:2022/09/15
"""
import os
import uuid
import yaml
import shutil
from pydantic import BaseModel
from app.utils.faas_sh import FunctionsCli
from app.core.config import settings
from app.models.mongo.tool_source import XmlToolSourceModel
from app.models.mongo.component import ComponentInstance
from app.models.mongo.fair import MarketComponentsInstallTaskModel
from app.utils.common import generate_uuid


class FunctionProvider(BaseModel):
    name: str = 'openfaas'
    gateway: str


class FunctionYaml(BaseModel):
    version: float = 1.0
    provider: FunctionProvider
    functions: dict

    def to_yaml(self, dst_path):
        with open(dst_path, 'w') as f:
            yaml.safe_dump(self.dict(), f)


class FunctionDeployer:

    def __init__(self, component_id, user_id):
        self.fs_cli = FunctionsCli.create_client()
        self.tool_ins = XmlToolSourceModel.objects(id=component_id).first()
        self.component_id = component_id
        self.user_id = user_id

    def create_yaml(self, yaml_path):
        fc = FunctionYaml(provider=FunctionProvider(gateway=settings.FaaS_GATEWAY),
                          functions={
                              'c' + self.tool_ins.id:
                                  {
                                      'lang': self.tool_ins.language.lower(),
                                      'handler': './c' + self.tool_ins.id,
                                      'image': settings.HARBOR_URL + "/datalab/python3.9:c" + self.tool_ins.id
                                  }
                          }
                          )
        fc.to_yaml(yaml_path)

    def create_requirements(self, file_path: str):
        with open(os.path.join(file_path, "requirements.txt"), 'w') as f:
            for _ in map(lambda x: f"{x.value}=={x.version}\n",
                         filter(lambda x: x.type == 'package', self.tool_ins.requirements)):
                f.write(_)

    def save_instance(self):
        ComponentInstance(id=str(uuid.uuid4()),
                          component_name=self.tool_ins.name,
                          synchronous_uri=settings.FUNCTION_DOMAIN + 'c' + self.tool_ins.id,
                          asynchronous_uri=settings.ASYNC_FUNCTION_DOMAIN + 'c' + self.tool_ins.id,
                          image_name=settings.HARBOR_URL + "/datalab/python3.9:c" + self.tool_ins.id,
                          docker_file="/tmp/template/python3-debian/Dockefile",
                          uri_type="asynchronous",
                          component_type='compute',
                          base_id=self.tool_ins.id
                          ).save()

    def create_temporary(self):
        install_task = MarketComponentsInstallTaskModel(id=generate_uuid(),
                                                        source=self.tool_ins,
                                                        installed_user=self.user_id,
                                                        reinstall=False,
                                                        reinstall_nums=0,
                                                        status="PULL",
                                                        source_type="NATIVE")
        install_task.save()
        try:
            print("Components downloaded，Start building component metadata")
            install_task.update(status="BUILD")
            _build_path = os.path.join(settings.BUILD_DIR, 'c' + self.tool_ins.id)
            if os.path.exists(_build_path):
                shutil.rmtree(_build_path)
            shutil.copytree(self.tool_ins.folder_path, _build_path)

            self.create_yaml(os.path.join(settings.BUILD_DIR, 'c' + self.tool_ins.id+'.yaml'))
            self.create_requirements(_build_path)
            self.fs_cli._yaml = 'c' + self.tool_ins.id+'.yaml'
            print("Components downloaded，Start building component metadata")
            install_task.update(status="DEPLOY")
            self.fs_cli.run(self.component_id, self.tool_ins.name, 'c' + self.tool_ins.id)
            self.save_instance()
        except Exception as e:
            print(e)
            install_task.update(status="FAILED")
        else:
            install_task.update(status="SUCCESS")

