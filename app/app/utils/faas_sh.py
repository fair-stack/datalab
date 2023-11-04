# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:faas_sh
@time:2022/09/13
"""
import time
import pathlib
import subprocess
from app.core.config import settings
from app.utils.middleware_util import get_redis_con
from app.utils.k8s_util.cluster import CloudCluster


class FunctionsCli:
    cli_scripts = "faas-cli"
    _yaml = None

    def __init__(self, gateway: str, user: str, password: str):
        self.gateway = gateway
        self.user = user
        self.password = password
        self.publisher = get_redis_con(1)

    @classmethod
    def create_client(cls):
        return cls(settings.FaaS_GATEWAY, settings.FaaS_USER, settings.FaaS_PASSWORD)

    def cmd_exec(self, command):
        child_process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, bufsize=1,
                                         stderr=subprocess.PIPE, cwd=settings.BUILD_DIR)
        return child_process

    @property
    def yaml(self):
        if self._yaml is None:
            raise ValueError('YAML Does not exist')
        return self._yaml

    @yaml.setter
    def yaml(self, value):
        if not pathlib.Path(value).exists():
            raise ValueError('YAML Does not exist')
        self._yaml = value

    @property
    def login_script(self):
        return " ".join([self.cli_scripts, "login",
                         "--username", self.user,
                         "--password", self.password,
                         "--gateway", self.gateway])

    @property
    def build_script(self):
        return " ".join([self.cli_scripts, "build",
                         "-f", self.yaml])

    @property
    def push_script(self):
        return " ".join([self.cli_scripts, "push",
                         "-f", self.yaml])

    @property
    def deploy_script(self):
        return " ".join([self.cli_scripts, "deploy",
                         "-f", self.yaml, "--gateway", self.gateway])

    @property
    def remove_script(self):
        return " ".join([self.cli_scripts, "remove",
                         self.function_name, "--gateway", self.gateway])

    @property
    def login(self):
        return self.cmd_exec(self.login_script)

    @property
    def build(self):
        return self.cmd_exec(self.build_script)

    @property
    def push(self):
        return self.cmd_exec(self.push_script)

    @property
    def deploy(self):
        return self.cmd_exec(self.deploy_script)

    @property
    def remove(self):
        return self.cmd_exec(self.remove_script)

    def run(self, components_id, function_name, tool_ins_id):
        self.function_name = function_name
        self.components_id = components_id
        login_info = self.login
        # remove_info = self.remove
        build_info = self.build
        push_info = self.push
        deploy_info = self.deploy
        step_list = ['build', 'push', 'deploy']
        for _ in iter(build_info.stdout.readline, b''):
            self.publisher.rpush(components_id, _)
        self.publisher.set(f"{components_id}-task", "build")

        subprocess.run(self.push_script, shell=True, stdout=subprocess.PIPE, bufsize=1, stderr=subprocess.PIPE, cwd=settings.BUILD_DIR)
        self.publisher.set(f"{components_id}-task", "push")

        for _ in iter(deploy_info.stdout.readline, b''):
            self.publisher.rpush(components_id, _)
        _cluster = CloudCluster()
        while True:
            print("tool_ins_id", tool_ins_id, "openfaas deploy")
            service_pod_status = _cluster.get_pod_status_blur(tool_ins_id, "openfaas-fn")
            if service_pod_status is True:
                break
            time.sleep(0.5)
        self.publisher.set(f"{components_id}-task", "deploy")

        # subprocess.run(self.push_script, shell=True, stdout=subprocess.PIPE, bufsize=1,
        #                                  stderr=subprocess.PIPE, cwd=settings.BUILD_DIR)
        # for _index, _info in enumerate([build_info, push_info, deploy_info]):
        #     for _line in iter(_info.stdout.readline, b''):
        #         self.publisher.rpush(components_id, _line)
        #         self.publisher.rpush(components_id, str(_info.poll()))
        #     _info.wait()
        #     self.publisher.set(f"{components_id}-task", step_list[_index])
        #     time.sleep(3)
