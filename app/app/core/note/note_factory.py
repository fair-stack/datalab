# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:note_factory
@time:2023/02/08
"""
import os
import yaml
from app.core.config import settings
from kubernetes import client, config
from app.models.mongo.notebook import UsedPortModel
config.load_kube_config(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                         "utils/k8s_util/config"))

from app.core.note.gateway import ApiSix


class NoteBookFactory:
    def __init__(self, app_id: str):
        self.tmp_file_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                         "utils/k8s_util/yamlTmplate/jpnb")
        self.deploy_yaml_tmp = os.path.join(self.tmp_file_dir, "notebook-deployment")
        self.svc_yaml_tmp = os.path.join(self.tmp_file_dir, "services.yml")
        self.namespace = "labnote"
        self.app_id = app_id
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()

    def create_deploy(self):
        # Modification
        _d = yaml.safe_load(open(self.deploy_yaml_tmp))
        _d["metadata"]["namespace"] = self.namespace
        _d["metadata"]["name"] = self.app_id
        _d["spec"]["selector"]["matchLabels"]["app"] = self.app_id
        _d["spec"]["template"]["metadata"]["labels"]["app"] = self.app_id
        _containers = list()
        for _ in _d["spec"]["template"]["spec"]["containers"]:
            _item = dict()
            for _k, _v in _.items():
                if _k == "name":
                    _v = self.app_id
                if _k == "command":
                    _v[2] = _v[2].replace('python template.py 035dcc', f"python template.py dupyter/{self.app_id}").replace("token=abcd", f"token={self.app_id}")
                _item[_k] = _v
            _containers.append(_item)
        _d["spec"]["template"]["spec"]["containers"] = _containers
        return _d

    def create_service(self):
        _d = yaml.safe_load(open(self.svc_yaml_tmp))
        _d["metadata"]["namespace"] = self.namespace
        _d["metadata"]["labels"]["app"] = self.app_id
        _d["metadata"]["name"] = "svc" + self.app_id
        _d["spec"]["selector"]["app"] = self.app_id
        _d['spec']['ports'][0]['nodePort'] = self.port
        return _d

    def get_port(self):
        _port = UsedPortModel.objects(used=False).first()
        _port.update(used=True)
        return _port.port

    def create_notebook(self):
        self.port = self.get_port()
        try:
            self.apps_api.create_namespaced_deployment(
                body=self.create_deploy(), namespace=self.namespace)

            self.core_api.create_namespaced_service(
                namespace=self.namespace,
                body=self.create_service(),
            )
        except:
            pass
        self.register_service()

    def register_service(self):
        as_gateway = ApiSix()
        as_gateway.register_jupyterlab_service(self.app_id,
                                               f"{settings.SERVER_HOST}:{self.port}",
                                               self.app_id, self.app_id)
        # as_gateway.register_jupyterlab_service(self.app_id, f"{self.app_id}.svc.{self.namespace}.svc.cluster.local:8888",
        #                                        self.app_id, self.app_id)
