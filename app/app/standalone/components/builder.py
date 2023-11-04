# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:builder
@time:2023/07/04
"""
import os
import uuid
import random
import shutil
import requests
from app.core.config import settings
from app.models.mongo.tool_source import XmlToolSourceModel
from app.models.mongo.component import ComponentInstance
from app.models.mongo.fair import MarketComponentsInstallTaskModel
from app.utils.common import generate_uuid
from app.service.manager.container import ContainerManager
# from app.app.service.manager.container import ContainerManager


class StandaloneFunctionDeployer:

    def __init__(self, component_id, user_id):
        self.tool_ins = XmlToolSourceModel.objects(id=component_id).first()
        self.component_id = component_id
        self.user_id = user_id
        self.port_min = 8080
        self.port_max = 9999
        self.port = None
        self.get_port()

    def get_port(self):
        used_ports = {i for i in ComponentInstance.objects.only("occupy") if i is not None}
        allow_ports = set([i for i in range(self.port_min, self.port_max)])
        wait_select = list(allow_ports.difference(used_ports))
        if not wait_select:
            raise ValueError("Not enough ports available，Unable to deploy cell")
        self.port = random.choice(wait_select)

    def create_requirements(self, file_path: str):
        with open(os.path.join(file_path, "requirements.txt"), 'w') as f:
            for _ in map(lambda x: f"{x.value}=={x.version}\n",
                         filter(lambda x: x.type == 'package', self.tool_ins.requirements)):
                f.write(_)

    def save_instance(self):
        ComponentInstance(id=str(uuid.uuid4()),
                          component_name=self.tool_ins.name,
                          synchronous_uri=f"{settings.STANDALONE_FUNCTION_DOMAIN}:{self.port}",
                          # Replace it withdockerAddress
                          asynchronous_uri=f"{settings.STANDALONE_FUNCTION_DOMAIN}:{self.port}",
                          image_name=settings.HARBOR_URL + "/datalab/python3.9:c" + self.tool_ins.id,
                          docker_file="/tmp/template/python3-debian/Dockefile",
                          uri_type="asynchronous",
                          component_type='compute',
                          base_id=self.tool_ins.id,
                          occupy=self.port
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
            install_task.update(status="BUILD")
            print("Components downloaded，Start building component metadata")
            _build_path = os.path.join(settings.BUILD_DIR, 'c' + self.tool_ins.id)
            if os.path.exists(_build_path):
                shutil.rmtree(_build_path)
            shutil.copytree("/home/cicd/datalab/app/app/standalone/template/dsp", _build_path)
            shutil.copytree(self.tool_ins.folder_path, f"{_build_path}/functions")
            self.create_requirements(f"{_build_path}/functions")
            containers = ContainerManager()
            containers.build(_build_path, self.port)
            install_task.update(status="DEPLOY")
            self.save_instance()
            # init_function(entrypoint="/code/functions",
            #               executable=self.tool_ins.executable,
            #               command=self.tool_ins.command,
            #               port=self.port)
        except Exception as e:
            print(e)
            install_task.update(status="FAILED")
        else:
            install_task.update(status="SUCCESS")


def init_function(entrypoint: str, executable: str, command: str, port: int):
    resp = requests.get(f'{settings.STANDALONE_FUNCTION_DOMAIN}:{port}/init/{entrypoint}/{executable}/{command}')
    print(resp.status_code)


if __name__ == '__main__':
    ...
