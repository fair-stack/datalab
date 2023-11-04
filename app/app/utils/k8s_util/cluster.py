# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:cluster
@time:2022/10/31
"""
import re
from kubernetes.client import CoreV1Api, ApiClient
from kubernetes import config
from kubernetes.client.rest import ApiException
from app.core.config import settings
config.kube_config.load_kube_config(config_file=settings.KUBERNETES_CONFIG)


class CloudCluster:
    def __init__(self):
        self.core = CoreV1Api()

    def get_pod_status(self, pod_name, namespace):
        _status = self.core.read_namespaced_pod(pod_name, namespace).status.phase
        if _status == "Running":
            return True
        return False

    def get_pod_status_blur(self, pod_name, namespace):
        for _ in self.core.list_namespaced_pod(namespace=namespace).items:
            function_name = _.metadata.labels['faas_function']
            if function_name == pod_name:
                return self.get_pod_status(_.metadata.name, namespace)

