# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:container
@time:2023/07/04
"""
import os
import shutil
import sys
import docker
import uuid
import requests
sys.path.append('/Users/wuzhaochen/Desktop/workspace/datalab/app')
from app.core.config import settings


class ContainerManager:

    def __init__(self):
        self._cli = docker.DockerClient(
            base_url=settings.DOCKER_TCP,
            version=settings.DOCKER_VERSION,
            timeout=settings.DOCKER_TIMEOUT)

    def status(self, container_id):
        return self._cli.containers.get(container_id).status

    def stop(self, container_id):
        try:
            self._cli.containers.get(container_id).stop()
        except Exception as e:
            return False
        else:
            return True

    def start(self, container_id):
        try:
            self._cli.containers.get(container_id).start()
        except Exception as e:
            print(e)
            return False
        else:
            return True

    def execute(self,
                shell: str,
                container_id: str
                ) -> str:
        """
        Example
            execute('./jupyter notebook', '69220156a0')
        """
        return self._cli.containers.get(container_id).exec_run(shell, user='root', workdir='/opt/conda/bin')[1].decode()

    @property
    def containers(self):
        return self._cli.containers.list()

    @property
    def all_containers(self):
        return self._cli.containers.list(all=True)

    @property
    def images(self):
        return self._cli.images.list()

    def creat_container(self, image, port: int):
        _container = self._cli.containers.create(
            image,
            ports={8080: port},
        )

        _container.start()
        return _container.id

    def build(self, path: str, port: int):
        build_info = self._cli.images.build(path=path, tag="dep:200000000000000000000")
        _image = build_info[0]
        self.creat_container(_image, port)
        print(_image)
        # shutil.rmtree(tmp_dir, ignore_errors=True)


def run_functions(port: int):
    post_data = {
        "lab_id": "20230706",
        "task_id": "20230706-2",
        "gateway_task_data":
            {"load_data": [
                {
                    "bucket": "d0e525f37bb2450cbd1992a779",
                    "object_name": "home/data_storage/storage_data/uploads_datasets_cache/d0e525f37bb2450cbd1992a779",
                    "file_type": "dir"
                },
                {
                    "bucket": "d0e525f37bb2450cbd1992a779",
                    "object_name": "home/data_storage/storage_data/uploads_datasets_cache/d0e525f37bb2450cbd1992a779",
                    "file_type": "dir"
                },
                {
                    "bucket": "287d251019dd45d0a5e4321bae",
                    "object_name": "home/data_storage/storage_data/uploads_datasets_cache/287d251019dd45d0a5e4321bae",
                    "file_type": "dir"
                },
                {
                    "bucket": "0993bc4a65fa4d638dcdcf44030f7194",
                    "object_name": "home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/uploads/vegmap_single",
                    "file_type": "dir"
                },
                {
                    "bucket": "0993bc4a65fa4d638dcdcf44030f7194",
                    "object_name": "home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/uploads/test.png",
                    "file_type": "file"
                }
            ],
                "upload_data": [{"bucket": "20230706", "object_name": "home"}]
            },
        "datalab_launch": {
            "package_dir": "/home/app/function",
            "file_name": "main.py",
            "function_name": "read_datasets"
        },
        "memory_output": [],
        "user_id": "0993bc4a65fa4d638dcdcf44030f7194",
        "datalab_env": {
            "REDIS_HOST": "127.0.0.1",
            "MONGO_HOST": "mongo-0.mongo.datalab.svc.cluster.local",
            "MINIO_URL": "127.0.0.1:9998",
            "MINIO__ACCESS_KEY": "admin",
            "MINIO_SECRET_KEY": "admin123",
            "OUTPUTS_POINT": None},
        "parameters": {
            "test_datasets": "home/data_storage/storage_data/uploads_datasets_cache/d0e525f37bb2450cbd1992a779",
            "test_list_datasets": [
                "home/data_storage/storage_data/uploads_datasets_cache/d0e525f37bb2450cbd1992a779",
                "home/data_storage/storage_data/uploads_datasets_cache/287d251019dd45d0a5e4321bae"],
            "test_boolean": True,
            "test_dir": "/home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/uploads/vegmap_single",
            "test_file": "/home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/uploads/test.png",
            "test_int": 2,
            "test_float": 1,
            "test_text": "xxx",
            "test_object": {"id": "afcbec358efe41518d07319610_75938c608627463bb8a5654a31"}
        }
    }

    resp = requests.post(f"http://127.0.0.1:{port}/", json=post_data,
                         headers={"X-Callback-Url": "http://127.0.0.1/api/components/callback/{_task_queue_id}"})
    print(resp.json())


if __name__ == '__main__':
    port = 8083
    print(settings.STANDALONE_MODEL)
    containers = ContainerManager()
    containers.build("/Users/wuzhaochen/Desktop/opensource/f6ba5ea1-39d8-432f-b712-b375794a9929/dse", port)
    # init_function(port)
    # run_functions(port)
    # import requests



    "docker run -d --name mycontainer -p 8087:8080 test:111"
    # for i in containers:
    #     print(i.__dict__)

