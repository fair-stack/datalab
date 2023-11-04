# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:storage
@time:2023/04/27
"""
import os
from datetime import datetime
from pathlib import Path
from app.models.mongo import DataFileSystem, UserModel
from app.models.mongo.public_data import PublicDatasetModel, PublicDataFileModel
from app.core.config import settings
from app.utils.common import generate_uuid
from app.utils.middleware_util import get_s3_client
from app.utils.uploads3_util import main as minio_uploader
import uuid
import os
from typing import Optional
from .lake import DataLakeManager


class FileTreeNode:
    extension = None
    name = None
    id = None
    parent = None
    model = None

    def __init__(self, absolute_path: str, user: UserModel, name: Optional[str] = None,
                 file_id: Optional[str] = None, parent: Optional[str] = None, root: bool = False):
        _parent, _name = absolute_path.rsplit('/', maxsplit=1)
        _model = DataFileSystem.objects(data_path=absolute_path).first()
        if parent is not None:
            _parent = parent
        if _model is not None:
            file_id = _model.id
            self.model = _model
            self.update_model()
        elif file_id is None:
            file_id = generate_uuid()
        if name is None:
            name = _name
        self.id = file_id
        self.name = name
        self.absolute_path = absolute_path
        self.extension = self.suffix
        self.child = None
        if self.is_dir:
            self.child = list()
        self.parent = "root" if root else _parent
        self.user = user

    @property
    def is_dir(self):
        return os.path.isdir(self.absolute_path)

    @property
    def suffix(self):
        _pattern_matching = self.absolute_path.split('/')[-1].rsplit('.', maxsplit=1)
        if self.is_dir or len(_pattern_matching) < 2:
            return "Unknown"
        return _pattern_matching[-1]

    @property
    def size(self):
        if self.is_dir:
            return 0
        return os.path.getsize(self.absolute_path)

    def dict(self):
        return {"id": self.id, "parent": self.parent, "absolute": self.absolute_path,
                "name": self.name, "child": [_child.dict() for _child in self.child] if self.is_dir else None,
                "extension":  self.extension, "is_dir": self.is_dir, "size": self.size}

    def update_model(self):
        # self.model.name = self.name
        # self.model.data_path = self.absolute_path
        # self.model.data_size = self.size
        # self.model.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # self.model.save()
        pass

    def orm_model(self):
        if self.model is None:
            DataFileSystem(
                id=self.id,
                name=self.name,
                is_file=not self.is_dir,
                is_dir=self.is_dir,
                store_name=self.absolute_path,
                data_size=self.size,
                data_path=self.absolute_path,
                user=user,
                from_source="UPLOADED",
                deleted=0,
                created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                data_type="myData",
                storage_service="ext4",
                deps=len(self.absolute_path.split('/')) - 2
            )


class FileTree:
    file_index = dict()

    def __init__(self, node: FileTreeNode, user: UserModel):
        self.root = node
        self.map = {node.absolute_path: node}
        if self.file_index:
            self.file_index.clear()
        self.file_index[node.absolute_path] = node.id
        self.user = user

    def create(self):
        for root, dirs, files in os.walk(self.root.absolute_path):
            for _dir in dirs:
                _absolute_path = os.path.join(root, _dir)
                self.create_dir_node(_absolute_path)
                print("CREATE", _absolute_path)
            for _file in files:
                _absolute_path = os.path.join(root, _file)
                self.create_file_node(_absolute_path)
                print("CREATE", _absolute_path)

    def create_dir_node(self, absolute_path: str):
        _parent_path = absolute_path.rsplit('/', maxsplit=1)[0]
        _node = FileTreeNode(absolute_path, user=self.user, parent=self.file_index.get(_parent_path))
        if self.file_index.get(_node.absolute_path) is None:
            self.file_index[_node.absolute_path] = _node.id
        self.map[_parent_path].child.append(_node)
        self.map[_node.absolute_path] = _node

    def create_file_node(self, absolute_path: str):
        _parent_path = absolute_path.rsplit('/', maxsplit=1)[0]
        _node = FileTreeNode(absolute_path, user=self.user,  parent=self.file_index.get(_parent_path))
        if self.file_index.get(_node.absolute_path) is None:
            self.file_index[_node.absolute_path] = _node.id
        self.map[_parent_path].child.append(_node)

    def create_index(self, node: FileTreeNode):
        self.file_index[node.absolute_path] = node.id

    def to_list(self):
        return self._list(node_list=list())

    def _list(self, node: Optional[FileTreeNode] = None, node_list: Optional[list] = []):
        if node is None:
            node = self.root
            node_list.append(node.dict())
        for _child in node.child:
            if _child.child is not None:
                self._list(_child, node_list)
            node_list.append(_child.dict())
        return node_list

    def list(self):
        self.create()
        return self.to_list()

    def to_service(self):
        _file_list = self.list()
        _root_node_size = sum([_['size'] for _ in _file_list])
        return _file_list, _root_node_size


class StorageManager:

    @staticmethod
    def save_datasets_file(absolute_path: str, file_name: str, datasets_id: str, user: UserModel, client):
        absolute_path_object = Path(absolute_path)
        standard_prefix = Path(settings.BASE_DIR, settings.DATA_PATH, f"uploads_datasets_cache/{datasets_id}/")
        _size = os.path.getsize(absolute_path)
        _model = PublicDataFileModel.objects(data_path=absolute_path).order_by('-updated_at').first()
        if _model is not None and _model.deleted is False:  # File already exists，This is an update.
            _model.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _model.name = Path(file_name).name
            _model.data_path = absolute_path
            _model.save()
        else:
            upload_path = Path(absolute_path.replace(str(standard_prefix), ""))
            for _p in upload_path.parents:
                if str(_p) != "/":  # non-directory
                    _dir_absolute_path = Path(standard_prefix, str(_p)[1:]).absolute()
                    print(f"Directory nesting{str(_dir_absolute_path)}")
                    _dir_model = PublicDataFileModel.objects(data_path=str(_dir_absolute_path)).first()
                    if _dir_model is None:
                        _dir_id = generate_uuid()
                        _dir_model = PublicDataFileModel(
                            id=_dir_id,
                            datasets=datasets_id,
                            name=_p.name,
                            is_file=False,
                            store_name=str(_dir_absolute_path),
                            data_size=0,
                            data_path=str(_dir_absolute_path),
                            user=user,
                            from_source="DATASETS",
                            deleted=0,
                            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            data_type="DATASETS",
                            storage_service="ext4",
                            deps=len(str(_p.absolute()).split('/'))-2
                        )
                        _dir_model.save()
                        # Whether the alignment size changes，The storage needs to be adjusted if there is a change
            _id = generate_uuid()
            _model = PublicDataFileModel(
                id=_id,
                datasets=datasets_id,
                name=Path(file_name).name,
                is_file=not absolute_path_object.is_dir(),
                store_name=absolute_path,
                data_size=_size,
                data_path=absolute_path,
                user=user,
                from_source="DATASETS",
                deleted=0,
                created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                data_type="DATASETS",
                storage_service="ext4",
                file_extension=absolute_path_object.suffix[1:],
                deps=len(str(upload_path).split('/'))-2
            )
            _model.save()
        minio_uploader(client, datasets_id, absolute_path, absolute_path, datasets_id)
        DataLakeManager().put(absolute_path, absolute_path, datasets_id)
        # client.fput_object(datasets_id, absolute_path, absolute_path)
        # Whether the alignment size changes，The storage needs to be adjusted if there is a change
        return _model

    @staticmethod
    def save_file(absolute_path: str, file_name: str, user:  UserModel):
        absolute_path_object = Path(absolute_path)
        standard_prefix = Path(settings.BASE_DIR, settings.DATA_PATH, user.id, "uploads/")
        _size = os.path.getsize(absolute_path)
        _model = DataFileSystem.objects(data_path=absolute_path).order_by('-updated_at').first()
        if _model is not None and _model.deleted is False:  # File already exists，This is an update.
            _model.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _model.name = Path(file_name).name
            _model.data_path = absolute_path
            _model.save()
            datasets_id = _model.id
            # Whether the alignment size changes，The storage needs to be adjusted if there is a change
        else:
            upload_path = Path(absolute_path.replace(str(standard_prefix), ""))
            for _p in reversed(upload_path.parents):
                if str(_p) != "/":  # non-directory, The root '/' Logo
                    _dir_absolute_path = Path(standard_prefix, str(_p)[1:]).absolute()
                    _dir_model = DataFileSystem.objects(data_path=str(_dir_absolute_path)).first()
                    print(f"Directory： {str(_dir_absolute_path)} --> {_dir_model}")
                    if _dir_model is None:
                        _dir_id = generate_uuid()
                        _parent = str(_p.parent)
                        _parent_id: str = "root" if _parent == "/" else \
                            DataFileSystem.objects(data_path=os.path.join(standard_prefix,
                                                                          str(_p.parent)[1:])).first().id
                        _dir_model = DataFileSystem(
                            id=_dir_id,
                            name=_p.name,
                            is_file=False,
                            is_dir=True,
                            store_name=str(_dir_absolute_path),
                            data_size=0,
                            data_path=str(_dir_absolute_path),
                            user=user,
                            from_source="UPLOADED",
                            deleted=0,
                            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            data_type="myData",
                            storage_service="ext4",
                            parent=_parent_id,
                            deps=len(str(_p.absolute()).split('/'))-2
                        )
                        _dir_model.save()
                    else:
                        _dir_model.deleted = False
                        _dir_model.save()
                        # Whether the alignment size changes，The storage needs to be adjusted if there is a change
            datasets_id = generate_uuid()
            _parent_id = os.path.join(standard_prefix, str(Path(file_name).parent)[1:])
            try:
                _parent_id = "root" if str(Path(file_name).parent) == "/" else \
                                DataFileSystem.objects(data_path=absolute_path.rsplit('/', maxsplit=1)[0]).first().id
            except Exception as e:
                print(e)
                _parent_id = "root"
            _model = DataFileSystem(
                id=datasets_id,
                name=Path(file_name).name,
                is_file=not absolute_path_object.is_dir(),
                is_dir=absolute_path_object.is_dir(),
                store_name=absolute_path,
                data_size=_size,
                data_path=absolute_path,
                user=user,
                from_source="UPLOADED",
                deleted=0,
                created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                data_type="myData",
                storage_service="ext4",
                file_extension=absolute_path_object.suffix[1:],
                deps=len(str(upload_path).split('/'))-2,
                parent=_parent_id
            )
            _model.save()
        client = get_s3_client()
        print(f"Push parameters {datasets_id} {absolute_path} {datasets_id}")
        minio_uploader(client, user.id, absolute_path, absolute_path, datasets_id)
        DataLakeManager().put(absolute_path, absolute_path, user.id)
        # Whether the alignment size changes，The storage needs to be adjusted if there is a change
        return _model

    @staticmethod
    def delete(model_id: str):
        _model = DataFileSystem.objects(id=model_id).first()
        if _model is None:
            return False
        _model.deleted = True

    @staticmethod
    def from_dir(absolute_path: str, user: UserModel):
        root_node = FileTreeNode(absolute_path=absolute_path,  user=user, root=True)
        _tree = FileTree(root_node, user)
        _tree.to_service()
        _nodes, _total_size = _tree.to_service()
        for i in _nodes:
            print(i)
        print(_total_size)
