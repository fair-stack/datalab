import os
import yaml
from kubernetes import client, config
from typing import Union, IO
from kubernetes.client.rest import ApiException
from app.utils import init_oep_logger


class K8sSdk:

    def __init__(self, names_pace='default'):
        config.load_kube_config(os.path.join(os.path.dirname(__file__), r'config'))
        self.apps_api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()
        self.namespace = names_pace
        self.logger = init_oep_logger(name=f'{__name__}.{self.__class__.__name__}')

    def load_yaml(self, file: Union[IO, str]) -> dict:
        if type(file) is IO:
            data = yaml.safe_load(file)
        elif isinstance(file, str):
            with open(file) as f:
                data = yaml.safe_load(f)
        else:
            data = dict()
            self.logger.warning(f'load yaml waring the param file is {type(file)}')
        return data

    def creat_deployment(self, source: dict):
        if isinstance(source, str):
            dep = self.load_yaml(source)
        elif isinstance(source, dict):
            dep = source
        else:
            dep = dict()
            self.logger.error(f"Creat Deloyment Erro  Source type Must be Dict or File Path,"
                              f"Input Type is {type(source)}")
        try:
            resp = self.apps_api.create_namespaced_deployment(
                body=dep, namespace="default")
            self.logger.info("Deployment created. status='%s'" % resp.metadata.name)
        except ApiException as e:
            self.logger.error(f"Exception with {e} from create_deployment")

    def create_service(self, body: dict):
        """
        :param body: service creat body
        :return:
        """
        try:

            self.core_api.create_namespaced_service(
                namespace=self.namespace,
                body=body,
            )
            self.logger.info('Create Service .....')
        except Exception as e:
            self.logger.error(f'Create Service Faild with {e}')

    def creat_pds(self, file_path: list, pvc_name, deoloyment_name, services_name):
        pass

    @property
    def deployments(self):
        return self.apps_api.list_deployment_for_all_namespaces()

    @property
    def services(self):
        return self.core_api.list_service_for_all_namespaces()

    @property
    def pvc(self):
        return self.core_api.list_namespaced_persistent_volume_claim(namespace=self.namespace)

    def creat_deployment_yaml(self, pod_pvc_name='juice-pvc',  pvc_name='test-pvc', container_port=1881,
                              pod_name='jfs-oeps'):
        try:
            data = self.load_yaml(os.path.dirname(__file__), 'yamlTmplate/Deployment.yml')
            data['metadata']['name'] = pod_name
            data['spec']['selector']['matchLabels']['app'] = pod_name
            data['spec']['template']['metadata']['labels']['app'] = pod_name
            if not data['spec']['template']['spec']['containers']:
                data['spec']['template']['spec']['containers'] = [{
                    'name': pod_name,
                    'image': '127.0.0.1:30080/k8s/jfs:latest',
                    'command': ['/bin/sh', '-ce', 'tail -f /dev/null'],
                    'ports': [
                        {'containerPort': container_port}
                    ],
                    'volumeMounts': [
                        {'mountPath': '/config', 'name': 'web-data'}
                    ]
                }]
            else:
                data['spec']['template']['spec']['containers'][0]['name'] = pod_name
                data['spec']['template']['spec']['containers'][0]['command'] = ['/bin/sh', '-ce', 'tail -f /dev/null']
                data['spec']['template']['spec']['containers'][0]['ports'] = [{'containerPort': container_port}]
                data['spec']['template']['spec']['containers'][0]['volumeMounts'] = [
                    {'mountPath': '/data', 'name': pod_pvc_name}]
            if not data['spec']['template']['spec']['volumes']:
                data['spec']['template']['spec']['volumes'] = [
                    {
                        'name': pod_pvc_name,
                        'persistentVolumeClaim': {
                            'claimName': pvc_name
                        }
                    }
                ]
            else:
                data['spec']['template']['spec']['volumes'][0]['name'] = pod_pvc_name
                data['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = pvc_name

            return data
        except Exception as e:
            self.logger.error(f'Create Deployment Yaml Faild with {e}')
            return None

    def create_service_yaml(self, name, dep_name, container_port,node_port, type='ClusterIP'):
        """
        :param name: app name
        :param container_port: port
        :param file_path: yaml file creat body
        :param type: ClusterIp or NodePort
        :return:
        """
        try:
            with open(os.path.join(os.path.dirname(__file__), 'yamlTmplate/services.yml')) as f:
                body = yaml.safe_load(f)
            if type == 'ClusterIP' or type == 'NodePort':
                body['metadata']['name'] = name
                body['metadata']['labels']['app'] = dep_name
                body['spec']['selector']['app'] = dep_name
                body['metadata']['spec'] = dict(type=type,
                                                selector={'app': name},
                                                ports=[
                                                    {'protocol': 'TCP',
                                                     'port': container_port,
                                                     'nodePort': node_port,
                                                     'targetPort': container_port
                                                     }
                                                ]
                                                )

                return body
            else:
                self.logger.warning(f"""Input param type:{type} is not NodePort or ClusterIP default is ClusterIP""")
                return None
        except Exception as e:
            self.logger.error(f'Create Service Yaml Faild with {e}')
            return None

    def creat_pvc_yaml(self, name, storage='50Gi'):
        try:
            body = self.load_yaml(os.path.join(os.path.dirname(__file__), 'yamlTmplate/pvc.yaml'))
            body['metadata']['name'] = name
            body['spec']['resources']['requests']['storage'] = storage
            self.core_api.create_namespaced_persistent_volume_claim(namespace='default',
                                                                         body=body)
        except Exception as e:
            self.logger.error(f"Creat PVC Faild with {e}")
