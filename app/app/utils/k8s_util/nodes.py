# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:nodes
@time:2022/10/31
"""
from app.core.config import settings
import re
from kubernetes.client import CoreV1Api, ApiClient
from kubernetes import config
from kubernetes.client.rest import ApiException
config.kube_config.load_kube_config(config_file=settings.KUBERNETES_CONFIG)


class K8SNode:
    def __init__(self, core: CoreV1Api = None):
        self.core = core
        if core is None:
            self.core = CoreV1Api()

    def get_nodes(self):
        try:
            return self.core.list_node()
        except ApiException as e:
            print(f"Failed to obtain cluster node information {e}")

    def read_nodes(self, node):
        try:
            return self.core.read_node(name)
        except ApiException as e:
            print(f"Failed to read node information {e}")

    def get_nodes_details(self):
        data = []
        k8s_object_list = self.get_nodes()
        total_memory = 0
        total_allocatable_memory = 0
        total_cpu = 0
        total_allocatable_cpu = 0

        for item in k8s_object_list.items:

            node_total_memory_gb = round((int(re.sub('\D', '', item.status.capacity['memory'])) / 1024 ** 2), 1)
            node_allocatable_memory_gb = round((int(re.sub('\D', '', item.status.allocatable['memory'])) / 1024 ** 2),
                                               1)

            node_cpu = int(item.status.capacity['cpu'])
            node_allocatable_cpu = int(item.status.allocatable['cpu'])

            total_memory += node_total_memory_gb
            total_allocatable_memory += node_allocatable_memory_gb
            total_cpu += node_cpu
            total_allocatable_cpu += node_allocatable_cpu
            if 'kubernetes.io/role' in item.metadata.labels:
                tag = item.metadata.labels['kubernetes.io/role']
            elif 'node.kubernetes.io/role' in item.metadata.labels:
                tag = item.metadata.labels['node.kubernetes.io/role']
            elif 'node-role.kubernetes.io/master' in item.metadata.labels:
                tag = 'master'
            elif 'node-role.kubernetes.io/node' in item.metadata.labels:
                tag = 'node'
            elif 'node-role.kubernetes.io/etcd' in item.metadata.labels:
                tag = 'etcd'
            else:
                tag = 'others'

            data.append({"NodeName": item.metadata.name,
                         "role": tag,
                         "node_allocatable_cpu": node_allocatable_cpu,
                         "node_allocatable_memory": node_allocatable_memory_gb,
                         "node_total_memory": node_total_memory_gb,

                         "os": item.status.node_info.os_image,
                         })
        return {"total_memory": total_memory,
                "total_allocatable_memory": total_allocatable_memory,
                "total_cpu": total_cpu,
                "total_allocatable_cpu": total_allocatable_cpu,
                "node_detail": data}

    def node_phase(self, node_name):
        self.core.read_node("0ce870a7aa6d4cc8ba34bd0115running")



