# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:lake
@time:2023/06/16
"""
import sys
sys.path.append('/Users/wuzhaochen/Desktop/workspace/datalab/app')
import zipfile
from io import BytesIO
from typing import Optional
from urllib.parse import quote
from app.core.config import settings
from app.models.mongo import UserModel, ExperimentModel, AnalysisModel2, TaskQueueModel, DataFileSystem
from datetime import datetime
from lakefs_client import models, Configuration
from lakefs_client.client import LakeFSClient
from lakefs_client.exceptions import NotFoundException, ApiException, ServiceException


class DataLakeManager:
    def __init__(self):
        self._repository = None
        self.configuration = Configuration()
        self.configuration.username = settings.LAKE_ADMIN_USERNAME
        self.configuration.password = settings.LAKE_ADMIN_TOKEN
        self.configuration.host = settings.LAKE_ADMIN_URL
        self.client = LakeFSClient(self.configuration)

    def list_branches(self, branches: str = "quickstart", results: bool = True):
        try:
            _branches = self.client.branches.list_branches(branches)
        except NotFoundException as e:
            return False, e.body
        else:
            if results is True:
                return True, _branches.results
            else:
                return True, _branches

    def create_branches(self, repository: str, branches_name: str, source: str = "main"):
        self.client.branches.create_branch(repository=repository,
                                           branch_creation=models.BranchCreation(
                                               name=branches_name,
                                               source=source)
                                           )

    def put(self, abstract_path: str, storage_path: str, repository: str, branch: str = "main"):
        print(abstract_path)
        print(repository)
        if not self.repository_exits(repository):
            self.create_repo(repository)
        with open(abstract_path, 'rb') as f:
            self.client.objects.upload_object(
                repository=repository,
                branch=branch,
                path=storage_path,
                content=f)
        try:
            commit_id = self.commit(repository, branch, msg=f"{str(datetime.utcnow())}", metadata={"lab": "test_insert"})
            # TODO Put into storage
            print("Metadata needs to be recorded！", commit_id)
        except ApiException as e:
            return False, e.body
        else:
            return commit_id

    def get(self, repository: str,  path: str, branch: str = "main"):
        _range = "bytes=0-1023"
        _pre_sign = True
        try:
            _io_stream = self.client.objects.get_object(repository, branch, path, range=_range, presign=_pre_sign)
        except ServiceException as e:
            print(e.body)
        finally:
            _io_stream = self.client.objects.get_object(repository, branch, path)
        return _io_stream

    def commit(self, repository: str, branch: str = "main", msg: str = "", metadata: Optional[dict] = None):
        try:
            _results = self.client.commits.commit(
                repository=repository,
                branch=branch,
                commit_creation=models.CommitCreation(message=msg,
                                                      metadata=metadata if metadata is not None else dict()))
        except ApiException as e:
            return False, e.body
        else:
            return True, _results.id

    def diff_branch(self, repository: str, branch: str = "main"):
        # Determine if there is a change difference under the branch
        try:
            _diff = self.client.branches.diff_branch(repository=repository, branch=branch).results
        except ApiException as e:
            return False, e.body
        else:
            if _diff:
                return True, _diff
            else:
                return True, None

    def diff_refs(self, repository: str, left_on: str, right_on: str):
        # Determine if there are any differences between the two branches under the same repository
        try:
            _diff = self.client.refs.diff_refs(repository=repository,
                                               left_ref=left_on,
                                               right_ref=right_on).results
        except ApiException as e:
            return False, e.body
        else:
            if _diff:
                return True, _diff
            else:
                return True, None

    def merge_branch(self, repository: str, source_branch: str, destination_branch: str):
        # Merge the two branch data
        try:
            _result = self.client.refs.merge_into_branch(
                repository=repository,
                source_ref=source_branch,
                destination_branch=destination_branch)
        except ApiException as e:
            return False, e.body
        else:
            return _result

    def list_objects(self, repository: str, branch: str = "main", prefix=None):
        _result = self.client.objects.list_objects(repository, branch, user_metadata=True, prefix=prefix).results
        return _result

    def get_commit_metadata(self, repository: str, commit_id: str):
        try:
            _result = self.client.commits.get_commit(repository, commit_id)
        except ApiException as e:
            return False, e.body
        else:
            return _result

    def create_repo(self, name: str, storage_namespace: Optional[str] = None, default_branch: str = "main"):
        if storage_namespace is None:
            storage_namespace = f'local://{name}'
        repo = models.RepositoryCreation(name=name,
                                         storage_namespace=storage_namespace,
                                         default_branch=default_branch)
        self.client.repositories.create_repository(repo)

    def repository_exits(self, repository: str) -> bool:
        try:
            if repository is None:
                raise ValueError("The repository prohibits the use of illegal characters")
            self.client.repositories.get_repository(repository)
        except NotFoundException:
            return False
        else:
            return True

    def download(self, model: DataFileSystem):
        if model.from_source == "UPLOADED":
            repository = model.user.id
        else:
            repository = model.lab_id
        if model.is_dir:
            response_file_name = f"{model.name}.zip"
            file_objects = list()
            for i in self.list_objects(repository=repository, prefix=model.data_path):
                file_objects.append({"name": i['path'].rsplit('/')[-1], "stream": self.get(repository, i['path'])})
            file_object = BytesIO()
            with zipfile.ZipFile(file_object, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for _ in file_objects:
                    zip_file.writestr(_['name'], _['stream'].read())
                zip_file.close()
                "application/x-zip-compressed"
            streaming = iter([file_object.getvalue()])

        else:
            response_file_name = model.name
            streaming = self.get(repository, path=model.data_path)
        return quote(response_file_name), streaming
    # @property
    # def repository_exits(self) -> bool:
    #     try:
    #         if self.repository is None:
    #             raise ValueError("The repository prohibits the use of illegal characters")
    #         self.client.repositories.get_repository(self._repository)
    #     except NotFoundException:
    #         return False
    #     return True
    #
    # @property
    # def repository(self):
    #     return self._repository
    #
    # @repository.setter
    # def repository(self, value):
    #     # It has to beUserID , ExperimentEntity, AnalysisEntityOne of them.
    #     # TaskQueueModel Associate all computation events
    #     experiment_entity = ExperimentModel.objects(id=value).first()
    #     analysis_entity = AnalysisModel2.objects(id=value).first()
    #     user_model = UserModel.objects(id=value).first()
    #     if analysis_entity is None and experiment_entity is None and user_model is None:
    #         raise ValueError("Storage creation failed，Abnormal spatial identifier")
    #     self._repository = value


if __name__ == '__main__':
    print(quote("02-Experiment-Experiment-Level 1 data state.jpg"))
    # from app.utils.middleware_util import get_s3_client
    # client = get_s3_client()
    # print(type(client.get_object("0993bc4a65fa4d638dcdcf44030f7194","home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/uploads/test.png").read()))
    # lake = DataLakeManager()
    # # print(lake.list_objects("0993bc4a65fa4d638dcdcf44030f7194", prefix='/home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194'))
    # streaming = lake.get("0993bc4a65fa4d638dcdcf44030f7194", path='/home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/uploads/test.png')
    # print(type(streaming))
