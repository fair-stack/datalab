# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:executor
@time:2022/08/04
"""
import docker
from typing import Union
from pathlib import Path
from app.core.config import settings


class ContainerManger:

    def __init__(self,
                 base_url: str = settings.DOCKER_TCP,
                 version: str = settings.DOCKER_VERSION,
                 timeout: int = settings.DOCKER_TIMEOUT,
                 ):
        if base_url is None:
            self._cli = docker.from_env()
        else:
            self._cli = docker.DockerClient(base_url=base_url, version=version, timeout=timeout)

    def status(self, container_id):
        return self._cli.containers.get(container_id).status

    def stop(self, container_id: str) -> bool:
        try:
            self._cli.containers.get(container_id).stop()
        except Exception as e:
            print(e)
            return False
        else:
            return True

    def start(self, container_id: str) -> bool:
        try:
            self._cli.containers.get(container_id).start()
        except Exception as e:
            print(e)
            return False
        else:
            return True

    def load_from_images(self):
        pass

    def execute(self,
                shell: str,
                container_id: str
                ) -> str:
        """
        Example
            execute('./histogram -params')
        """
        return self._cli.containers.get(container_id).exec_run(shell, user='root', workdir='/work/tmp/')[1].decode()

    @property
    def containers(self) -> list:
        return self._cli.containers.list()

    @property
    def all_containers(self) -> list:
        return self._cli.containers.list(all=True)

    @property
    def images(self) -> list:
        return self._cli.images.list()

    def creat_container(self, image_name: str, container_port: int) -> str:
        _container = self._cli.containers.create(
            self._cli.images.get(image_name),
            command=f'python3 main.py --port {container_port}',
            ports={container_port: container_port},
            working_dir='/work/datalab-component'
        )
        _container.start()
        return _container.id

    def build_image(self, path: Union[str, Path], tag: str):
        return self._cli.images.build(path=path, tag=tag)

    def delete_image(self, image_id: str):
        try:
            self._cli.images.remove(image_id)
        except Exception as e:
            return str(e)
