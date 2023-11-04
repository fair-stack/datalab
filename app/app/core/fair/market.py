# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:market
@time:2023/01/11
"""
import os
import zipfile
import pathlib
import requests
from typing import Optional
from app.utils.middleware_util import get_redis_con
from app.core.deploy_functions import FunctionDeployer
from datetime import datetime
from app.core.config import settings
from app.utils.common import generate_uuid
from app.utils.k8s_util.nodes import K8SNode
from app.utils.tool_util.xml_parser import XmlToolSource
from app.models.mongo.fair import (
    FairMarketComponentsModel,
    FairMarketComponentsTreeModel,
    MarketComponentsInstallTaskModel,
    VisualizationComponentModel,
)

from app.models.mongo.public_data import PublicDatasetModel
from app.models.mongo import AnalysisModel2, ExperimentModel, NoteBookProjectsModel, XmlToolSourceModel, \
    UserModel


class FairMarketComponent:

    def __init__(self, component_id: Optional[str] = None, user_id: Optional[str] = None):
        self.market_api = settings.MARKET_API
        self.component_id = component_id
        self.user_id = user_id
        self.file_name = None
        self.folder_name = None
        self._fmc = FairMarketComponentsModel.objects(id=component_id).first()

    def download_component(self):
        component_id = self.component_id
        _d = FairMarketComponentsModel.objects(id=component_id).first()
        if _d is None:
            raise FileNotFoundError
        if _d.componentType == settings.FRONTEND_COMPONENT:
            download_dir = pathlib.Path(settings.MARKET_FRONT_COMPONENT_DOWNLOAD_CACHE_DIR)
            component_download_path = pathlib.Path(settings.MARKET_FRONT_COMPONENT_DOWNLOAD_CACHE_DIR, component_id)
            unzip_path = pathlib.Path(settings.MARKET_FRONT_COMPONENT_DOWNLOAD_DIR, component_id)

        else:
            download_dir = pathlib.Path(settings.MARKET_COMPONENT_DOWNLOAD_DIR)
            component_download_path = pathlib.Path(settings.MARKET_COMPONENT_DOWNLOAD_DIR, component_id)
            unzip_path = pathlib.Path(settings.MARKET_COMPONENT_DOWNLOAD_DIR, component_id)
        if not download_dir.exists():
            os.makedirs(download_dir)
        if component_download_path.exists():
            print("The component source code already exists")
        download_url = f'{self.market_api}/download?id={component_id}'
        response = requests.get(download_url, stream=True)
        _response_headers_file = response.headers['Content-Disposition'].split('attachment; filename=')[-1]
        self.folder_name = _response_headers_file.replace('.zip', '')
        with open(component_download_path.__fspath__()+'dist.zip', 'wb') as f:
            for _r in response.iter_content(chunk_size=1024):
                if _r:
                    f.write(_r)
        with zipfile.ZipFile(component_download_path.__fspath__()+'dist.zip') as z:
            z.extractall(unzip_path.__fspath__())

    def get_market_component(self):
        # response = requests.get(f'{self.market_api}/private').json()
        response = list()
        response.extend(requests.get(f'{self.market_api}/private?software=DataLab').json()['data']['list'])
        response.extend(requests.get(f'{self.market_api}/private?software=DataSpace').json()['data']['list'])
        # for _ in response['data']['list']:
        for _ in response:
            if _.get('bundle') is None:
                _['bundle'] = '123'
            _c = FairMarketComponentsModel.objects(id=_['Id']).first()
            if _c is None:
                _fmc = FairMarketComponentsModel(
                    **self.transform(_)
                )
                _fmc.save()
                if _fmc.componentType == "front-end":
                    _support = list()
                    _response_schema = list()
                    for _p in _fmc.parameters:
                        _key = _p.get("key")
                        _value = _p.get("value")
                        if _key == "suffix" and _value is not None:
                            _support.extend(_value.split(','))
                        elif _key == "data" and _value is not None:
                            _response_schema.append(_value)
                    _vs = VisualizationComponentModel(id=generate_uuid(), source=_fmc, support=_support,
                                                      response_schema=_fmc.parameters, create_at=_fmc.CreateAt,
                                                      update_at=_fmc.UpdateAt, name=_fmc.name,)
                    _vs.save()
                category = FairMarketComponentsTreeModel.objects(category=_['category']).first()
                if category is None:
                    FairMarketComponentsTreeModel(id=generate_uuid(),
                                                  category=_['category']).save()

                else:
                    category.update(counts=category.counts + 1)
        return FairMarketComponentsModel.objects

    def transform(self, data: dict):
        data.pop('downloadCount')
        data.pop('softwareObject')
        self.folder_name = data['name']
        data['id'] = data.pop('Id')
        data.pop('reviewRemark')
        data['CreateAt'] = datetime.strptime(data['CreateAt'], "%Y-%m-%dT%H:%M:%S.%fZ")
        data['UpdateAt'] = datetime.strptime(data['UpdateAt'], "%Y-%m-%dT%H:%M:%S.%fZ")
        return data

    def deploy(self):
        xml_tool_source = XmlToolSource(folder_name=self.folder_name,
                                        user_space=self.component_id,
                                        tool_path=settings.MARKET_COMPONENT_DOWNLOAD_DIR,
                                        user_id=self.user_id)
        parse_result = xml_tool_source.to_dict()
        try:
            data = parse_result.data
            document = XmlToolSourceModel(**data,
                                          id=generate_uuid(length=26))
            document.save()
            return document.id
            # Changing tasks
        except Exception as e:
            print(e)
            print(f'failed to save xml to db: {self.folder_name}')
        print(parse_result.data)

    def run(self):
        install_task = MarketComponentsInstallTaskModel.objects(source=self._fmc).first()
        if install_task is not None:
            install_task.update(reinstall_nums=install_task.reinstall_nums + 1,
                                reinstall=True)
            print("Start executing component installation tasks from the component marketplace,This task is to reinstall components")
        else:
            install_task = MarketComponentsInstallTaskModel(id=generate_uuid(),
                                                            source=self._fmc,
                                                            installed_user=self.user_id,
                                                            reinstall=False,
                                                            reinstall_nums=0,
                                                            status="PULL",
                                                            source_type="MARKET")
            install_task.save()
            print("Start executing component installation tasks from the component marketplace,This component is installed for the first time")
        try:
            print("Start downloading the component source bundle")
            self.download_component()
            print("Components downloaded，Start building component metadata")
        except Exception as e:
            print(f"Component download failed {e}")
            install_task.update(status="FAILED")
        if self._fmc.componentType == settings.FRONTEND_COMPONENT:
            install_task.update(status="SUCCESS")
            self._fmc.update(installed=True)
        else:
            try:

                install_task.update(status="BUILD")
                tool_ins_id = self.deploy()
                if tool_ins_id is not None:
                    print("Start deploying")
                    install_task.update(status="DEPLOY")
                    fd = FunctionDeployer(tool_ins_id)
                    fd.create_temporary()
                    publisher = get_redis_con(1)
                    publisher.rpush(tool_ins_id, "start")
                    publisher.set(f"{tool_ins_id}-task", "start")
                    publisher.close()
                    print("Component deployment is complete")
                else:
                    install_task.update(status="FAILED")
            except Exception as e:
                print(e)
                install_task.update(status="FAILED")
                pass
            else:
                install_task.update(status="SUCCESS")
                self._fmc.update(installed=True)


def fair_stack_report():
    physical_resources = K8SNode().get_nodes_details()
    post_data = {
        "userName": settings.MARKET_USER,
        "softwareId": "63b7fc6e94de2e92484b2363",
        "softwareName": "DataLab",
        "softwareVersion": settings.VERSION,
        "softwareData": {
            "AnalysisToolsCount": AnalysisModel2.objects.count(),
            "ExperimentCount": ExperimentModel.objects.count(),
            "InteractiveProgrammingCount": NoteBookProjectsModel.objects.count(),
            "ComponentCount": XmlToolSourceModel.objects.count(),
            "Cores": physical_resources['total_cpu'],
            "UsersCount": UserModel.objects.count(),
            "Memory": physical_resources['total_memory'],
            "PublicData": PublicDatasetModel.objects.count()
        }
    }
    try:
        url = settings.MARKET_API.replace('/api/v2/component', "/api/v2/open/software")
        resp = requests.post(url, data=post_data)
        print(resp.text)
    except Exception as e:
        print(f"Push exception！！！！{e}")
