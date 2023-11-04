import logging
import os.path
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Union, Optional
import re
from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
    Request
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from mongoengine import Q

from app.api import deps
from app.core.config import settings
from app.models.mongo import (
    DataFileSystem,
    UserModel,
)
from app.schemas import (
    DatasetUpdateSchema,
)
from app.usecases import datasets_usecase
from app.utils.common import generate_uuid, convert_mongo_document_to_data
from app.utils.file_util import chunked_copy, generate_dir, del_datasets
from app.utils.resource_util import check_storage_resource, cache_cumulative_sum

router = APIRouter()


@router.post("/file/upload",
             summary="Data file upload")
async def upload_dataset_file(
        request: Request,
        files: List[UploadFile],
        current_user: UserModel = Depends(deps.get_current_user)):
    """Uploading data files"""
    # Check if the storage directory for the user exists
    storage_path = Path(settings.BASE_DIR, settings.DATA_PATH, current_user.id)
    if not (storage_path.exists() and storage_path.is_dir()):
        storage_path.mkdir(parents=True)

    print(f'uploading <{len(files)}> files: {[file.filename for file in files]}')
    for file in files:
        print(f'uploading file: {file.filename}')

        _id = generate_uuid(length=26)  # Reference mongo len(objectId)=26

        filename = file.filename
        file_extension = filename.split(".")[-1] if "." in filename else None
        store_name = f'{_id}.{filename}'

        # Check if a file with the same name exists：Uploading files with the same name is not allowed
        store_path = Path(storage_path, store_name)
        if store_path.exists() and store_path.is_file():
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"file already exist: {store_path}"})
        # file.file is `file-like` object
        chunked_copy(file.file, store_path)
        logging.info(f"uploaded: {filename}")

        try:
            _size = os.path.getsize(store_path)
            # DataFileSystem Establish, write db
            dataFileSystem = DataFileSystem(
                id=_id,
                name=filename,
                is_file=True,
                is_dir=False,
                store_name=store_name,
                data_size=_size,  # Determining file size: byte
                data_path=store_path.as_posix(),
                user=current_user.id,
                from_source="UPLOADED",
                deleted=0,
                created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                data_type="myData",
                storage_service="ext4",
                file_extension=file_extension,
                deps=0
            )
            dataFileSystem.save()
            await cache_cumulative_sum(current_user.id, _size, filename, request.app.state.use_storage_cumulative)
        except Exception as e:
            print(e)
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                content={"msg": f"failed to save: {filename}"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})


@router.post("/folder/upload",
             summary="Data folder upload")
async def upload_dataset_folder(
        request: Request,
        file: UploadFile,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Uploading data files

    logic：
        - Front-end：Compress folders，Upload the zip file
        - Backend：Decompress the compressed package，And will dir write DataFileSystem    （Know dir The path information is sufficient，Subsequent displays can be positioned dir the children）
    """

    # Check if the storage directory for the user exists
    storage_path = Path(settings.BASE_DIR, settings.DATA_PATH, current_user.id)
    if not (storage_path.exists() and storage_path.is_dir()):
        storage_path.mkdir(parents=True)

    # .name Filename，Contains the suffix name，If it is a directory, get the directory name
    # .stem Filename，No suffixes
    # .suffix Suffix，For example .txt, .png
    # .parent Parent directory，Equivalent to cd ..

    # compressionFilename
    archive = file.filename
    # If archive thefile，the archive for "data/15.blob"，You need to become data.blob
    print(f"archive original: {archive}")

    # Compressed file format
    suffix = Path(archive).suffix
    archive_format = suffix.strip(".")

    # data/15 become data
    # strip(sequence) It's not gonna be sequence for Get rid of，traversalGet rid of sequence the
    # In reference to replace
    # _archive = archive.strip(suffix)
    _archive = archive.replace(suffix, "")
    archive = _archive.split("/")[0] + suffix
    print(f"archive normed: {archive}")

    # Folder name
    # "data/15.blob" the stem for 15，for data
    unpack = Path(archive).stem

    print(f'uploading archive: {archive}')

    _id = generate_uuid(length=26)  # Reference mongo len(objectId)=26

    archive_stored = f'{_id}.{archive}'
    unpack_stored = f'{_id}.{unpack}'

    # archive Storage path
    archive_stored_path = Path(storage_path, archive_stored)
    # Determines if the same name exists archive file
    if archive_stored_path.exists() and archive_stored_path.is_file():
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"archive already exist: {archive_stored_path}"})

    # unpack Storage path
    unpack_stored_path = Path(storage_path, unpack_stored)

    try:
        # file.file is `file-like` object
        # will archive filewritethePath ~/store_archive
        chunked_copy(file.file, archive_stored_path)
        logging.info(f"uploaded archive: {archive}")
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to upload archive: {archive}"})

    # Decompress
    try:
        # Decompress archive_stored file, According to different formats，Use the shutil or zipfile
        # theDecompressPath，theDecompressthe：
        # DecompressPathfor  ~/unpack_stored_path/ the：
        # shutil.unpack_archive the：  ~/unpack_stored_path/<inner_folder>/<content>， Among them <inner_folder> Automatic generation
        # zipfile thethe： ~/unpack_stored_path/<content>； for <folder>，DecompressPath ~/unpack_stored_path/<unpack>
        supported_unpack_formats = [f[0] for f in shutil.get_unpack_formats()]
        # Checking whether or not shutil the unpack_formats
        if archive_format in supported_unpack_formats:
            shutil.unpack_archive(filename=archive_stored_path,
                                  extract_dir=unpack_stored_path)
        else:
            # Use the zipfile
            with zipfile.ZipFile(archive_stored_path) as z:
                # for <folder>，DecompressPath ~/unpack_stored_path/<unpack>
                _unpack_stored_path = unpack_stored_path.joinpath(unpack)
                if not _unpack_stored_path.exists():
                    _unpack_stored_path.mkdir(parents=True)
                z.extractall(path=_unpack_stored_path)
        # Delete archive_stored
        archive_stored_path.unlink()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to unpack archive: {archive_stored_path}"})

    # Decompress：
    #  1. shutil.unpack_archive Decompress：    ~/unpack_stored_path/<inner_folder>/<content>
    #  2. zipfile.ZipFile Decompress：          ~/unpack_stored_path/<unpack>/<content>，Among them <unpack> for，See you on

    try:
        inner_folder_path = list(unpack_stored_path.iterdir())[0]
        # will   ~/unpack_stored_path/<folder>/<content> Copy to ~/unpack_stored_path/<content>，
        shutil.copytree(src=inner_folder_path,
                        dst=unpack_stored_path,
                        dirs_exist_ok=True)
        # Delete ~/unpack_stored_path/<folder>
        shutil.rmtree(inner_folder_path)
    except Exception as e:
        print(e)
        # DeleteDecompressPath
        shutil.rmtree(unpack_stored_path)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={
                                "msg": f"failed to move folder content: `{inner_folder_path}` -> `{unpack_stored_path}`"})

    # file，Create List[datasetSchema]， Create List[datasetModel]

    def iter_get_dir_sub_paths(root_path: Union[Path, str]) -> List[Path]:
        """
        Breadth first，take dir the path (Not included dir Self）
        :param root_path:
        :return:
        """
        from collections import deque

        q = deque()
        resp = list()
        root_path = Path(root_path)
        # will，Append to q the
        if root_path.is_dir():
            subs = list(root_path.iterdir())
            q.extendleft(subs)
        # Dynamic update q
        while q:
            path = q.pop()
            resp.append(path)
            if path.is_dir():
                path_subs = list(path.iterdir())
                q.extendleft(path_subs)
        return resp

    try:

        rootDataFileSystem = DataFileSystem(
            id=_id,
            name=unpack,
            is_file=False,
            is_dir=True,
            store_name=unpack_stored,
            data_size=0,  # FIXME: Determining file size: byte
            data_path=unpack_stored_path.as_posix(),
            user=current_user.id,
            from_source="UPLOADED",
            deleted=0,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data_type="myData",
            storage_service="ext4",
            deps=0
        )
        rootDataFileSystem.save()

        model_list = []

        # take root_dir the
        sub_paths = iter_get_dir_sub_paths(unpack_stored_path)
        for path in sub_paths:
            # Absolute path
            path = path.resolve()
            # DataFileSystem Establish, write db
            dataFileSystem = DataFileSystem(
                id=generate_uuid(length=26),
                name=path.name,
                is_file=path.is_file(),
                is_dir=path.is_dir(),
                store_name=path.name,
                data_size=os.path.getsize(path) if path.is_file() else None,  # Determining file size: byte
                data_path=path.as_posix(),
                user=current_user.id,
                from_source="DERIVED",  # DERIVED Not displayed directly at the first level of the data list
                deleted=0,
                created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                data_type="myData",
                storage_service="ext4",
                file_extension=path.suffix.strip(".") if path.is_file() else None,
                parent="unknown",
                deps=-1  # FIXME: the deps Not yet calculated，Temporary arrangement -1 logo
            )
            model_list.append(dataFileSystem)
            await cache_cumulative_sum(current_user.id, os.path.getsize(path) if path.is_file() else 0, path.name,
                                       request.app.state.use_storage_cumulative)
        # bulk insert
        DataFileSystem.objects.insert(model_list)
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "bulk insert success", "root_id": _id})
    except Exception as e:
        print(e)
        # DeleteDecompressPath
        shutil.rmtree(unpack_stored_path)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to save to model: {unpack_stored_path}"})


@router.post("/folder/create")
async def create_dataset_folder(
        name: str,
        parent: Union[str, None] = None,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    Createfile（for Analysis sets the output path）

    :param name:
    :param parent: Parent directory
    :param current_user:
    :return:
    """
    #
    dataset_id = generate_uuid(length=26)

    # Parent directory
    if isinstance(parent, str):
        parentDFS = DataFileSystem.objects(id=parent).first()
        if parentDFS is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={"msg": "parent dataset not found"})
        # JudgmentParent directory
        parent_path = parentDFS.data_path
        target_path = f"{parent_path}/{name}"
        # Judgment
        targetDFS = DataFileSystem.objects(data_path=target_path).first()
        if targetDFS is not None:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                                content={"msg": f"dataset with name [{name}] already exists"})
        #
        store_name = name
        deps = -1
    # Parent directoryfor root
    else:
        store_name = f"{dataset_id}.{name}"
        parent = "root"
        deps = 0
        #
        target_path = f"{settings.BASE_DIR}/{settings.DATA_PATH}/{current_user.id}/{store_name}"

    # New
    targetDFS = DataFileSystem(
        id=dataset_id,
        name=name,
        is_file=False,
        is_dir=True,
        store_name=store_name,  # Non-top level，No stitching uuid
        data_size=0,  # Determining file size: byte
        data_path=target_path,
        user=current_user.id,
        from_source="ANALYSIS",  # ANALYSIS Can be displayed at the first level in the data list
        deleted=0,
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        data_type="myData",
        storage_service="ext4",
        file_extension=None,
        parent=parent,
        deps=deps  # FIXME: the deps Not yet calculated，Temporary arrangement -1 logo
    )
    targetDFS.save()
    # Create
    try:
        # Check if the storage directory for the user exists
        storage_path = Path(target_path)
        if not (storage_path.exists() and storage_path.is_dir()):
            storage_path.mkdir(parents=True)
    except Exception as e:
        print(f"create_dataset_folder: {e}")
        # Delete
        targetDFS.delete()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to create folder [{name}]"})
    else:
        _data = convert_mongo_document_to_data(targetDFS)
        #
        data_path = _data.get("data_path")
        user = _data.get("user")
        _data['display_path'] = datasets_usecase.get_display_path(data_path, user_id=user)
        #
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content=jsonable_encoder(_data))


@router.get("/download",
            summary="Data download")
def download_dataset(
        dataset_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    file：Direct download
    file：After minifying and packing，Download

    :param dataset_id:
    :param current_user:
    :return:
    """

    storage_temp_path = Path(settings.BASE_DIR, settings.DATA_TEMP_PATH, current_user.id)
    if not (storage_temp_path.exists() and storage_temp_path.is_dir()):
        storage_temp_path.mkdir(parents=True)

    dataFileSystem = DataFileSystem.objects(id=dataset_id).first()
    if dataFileSystem is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "dataset not found"})

    # Path
    data_path = dataFileSystem.data_path
    # Does it exist
    if not data_path:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"data_path is missing for dataset: {dataset_id}"})

    data_path = Path(data_path)
    if not data_path.exists():
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"data_path not exists: {data_path}"})
    # Iffile，Direct download
    if data_path.is_file():
        filename = dataFileSystem.name
        return FileResponse(path=data_path, filename=filename, media_type="application/octet-stream")

    else:
        # Iffile: compression （Pathfor）  -> Download

        # TODO: Cleaning up temporary directories （storage_data_temp）the data？

        archive_name = dataFileSystem.name
        archive_format = "zip"
        archive_fullname = f"{archive_name}.{archive_format}"
        archive_path = storage_temp_path.joinpath(archive_fullname)

        # compression
        shutil.make_archive(base_name=str(storage_temp_path.joinpath(archive_name)),
                            format=archive_format,
                            root_dir=data_path)

        # send
        return FileResponse(path=archive_path, filename=archive_fullname, media_type="application/octet-stream")


@router.get("/",
            summary="Data list")
def read_datasets(
        q: Union[str, None] = None,
        is_dir: Union[bool, None] = None,
        page: int = 0,
        size: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Data list

    :param q:
    :param is_dir:
    :param page:
    :param size:
    :param current_user:
    :return:
    """
    skip = page * size

    # from_user nonempty： From sharing data，Filter out
    # query = Q(user=current_user.id) & Q(data_type="myData") & Q(from_user=None) & Q(deleted=False)
    query = Q(user=current_user.id) & Q(from_user=None) & Q(deleted=False)

    # Key words
    if q:
        # At this point，Unlimited from_source__ne == "DERIVED"
        query = query & Q(name__icontains=q)
    else:
        # Only the first layer is retrieved
        query = query & Q(deps=0)

    # is_dir
    if isinstance(is_dir, bool):
        query = query & Q(is_dir=is_dir)

    total = DataFileSystem.objects(query).count()

    # [] if not exists
    dataFileSystem_list = DataFileSystem.objects(query).order_by("-created_at")[skip: skip + size]
    # serialization
    # Note：DataFileSystem the user [ReferenceField]，Can't be used directly DatasetV2Schema the user [str]
    data_list = []

    root = f"{settings.BASE_DIR}/{settings.DATA_PATH}/"

    for d in dataFileSystem_list:
        _data = convert_mongo_document_to_data(d)
        #
        data_path = _data.get("data_path")
        user = _data.get("user")
        _data['display_path'] = datasets_usecase.get_display_path(data_path, user_id=user)
        #
        data_list.append(_data)
    content = {"msg": "success",
               "total": total,
               "data": data_list}

    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/{dataset_id}",
            summary="Data Details")
def read_dataset(
        dataset_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    """Data Details"""
    dataFileSystem = DataFileSystem.objects(id=dataset_id).first()
    # serialization
    # Note：DataFileSystem the user [ReferenceField]，Can't be used directly DatasetV2Schema the user [str]
    if dataFileSystem is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "dataset not found"})
    _data = convert_mongo_document_to_data(dataFileSystem)
    #
    data_path = _data.get("data_path")
    user = _data.get("user")
    _data['display_path'] = datasets_usecase.get_display_path(data_path, user_id=user)
    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(_data))


@router.get("/iterdir/{id}",
            summary="traversalfile")
def iterdir_dataset(id: str,
                    data_path: str,
                    is_dir: Union[bool, None] = None,
                    current_user: UserModel = Depends(deps.get_current_user)):
    """
    According to id and data_path，traversal data_path，Return to the subordinate（Level 1 only）the files/folders

    :param id:
    :param data_path:
    :param is_dir:
    :param current_user:
    :return:
    """

    # Path Path
    # .name Filename，Contains the suffix name，If it is a directory, get the directory name
    # .stem Filename，No suffixes
    # .suffix Suffix，For example .txt, .png
    # .parent Parent directory，Equivalent to cd ..
    # .anchor anchor，the C:\ or /

    # Judgment dataset_id and user matching
    # TODO: thelogic
    # Whether conditions are required `user`
    dataFileSystem = DataFileSystem.objects(id=id).first()
    # serialization
    # Note：DatasetModel the user [ReferenceField]，Can't be used directly DatasetV2Schema the user [str]
    if dataFileSystem is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "dataset not found"})

    dataFileSystem_data = convert_mongo_document_to_data(dataFileSystem)

    # children
    children = []

    # iter the path (Use the resolve takeAbsolute path)
    root_path = Path(data_path).resolve()
    if not root_path.exists():
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"data_path not exists: {root_path}"})
    elif not root_path.is_dir():
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"data_path is not dir: {root_path}"})
    else:
        path_list = list(root_path.iterdir())
        for path in path_list:
            # store_name file，In reference to data_path Judgment
            sub_dataFileSystem = DataFileSystem.objects(data_path=path.as_posix()).first()
            if sub_dataFileSystem is None:
                continue
            else:
                # Judgment is_dir
                if isinstance(is_dir, bool):
                    if sub_dataFileSystem.is_dir != is_dir:
                        continue
                #
                child = {
                    'id': sub_dataFileSystem.id,
                    "name": sub_dataFileSystem.name,
                    "is_file": sub_dataFileSystem.is_file,
                    "file_extension": sub_dataFileSystem.file_extension,
                    "data_path": path.as_posix(),
                    "user": dataFileSystem_data.get("user"),
                    "parent_dir": root_path.as_posix(),
                    "display_path": datasets_usecase.get_display_path(data_path=path.as_posix(),
                                                                      user_id=dataFileSystem_data.get("user"))
                }
                children.append(child)

    # Paththe
    # cur_parent_dir = str(root_path.parent)
    cur_parent_dir = root_path.parent.as_posix()
    cur_parent = DataFileSystem.objects(data_path=cur_parent_dir).first()
    if cur_parent is None:
        cur_parent_dir = None
        cur_parent_id = None
    else:
        cur_parent_id = cur_parent.id

    content = {
        'id': id,
        'name': dataFileSystem_data.get("name"),
        'dir': root_path.as_posix(),
        'children': children,
        'parent_id': cur_parent_id,
        'parent_dir': cur_parent_dir
    }
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.put("/{dataset_id}",
            summary="Metadata updates")
def update_dataset(
        dataset_id: str,
        updates: DatasetUpdateSchema,
        current_user: UserModel = Depends(deps.get_current_user)):
    """Data Details"""
    description = updates.description
    DataFileSystem.objects(id=dataset_id).update_one(
        description=description,
        updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    # Querying
    dataFileSystem = DataFileSystem.objects(id=dataset_id).first()
    # serialization
    # Note：DatasetModel the user [ReferenceField]，Can't be used directly DatasetV2Schema the user [str]
    if dataFileSystem is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "dataset not found"})
    _data = convert_mongo_document_to_data(dataFileSystem)
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(_data))


@router.delete("/{dataset_id}",
               summary="Delete")
async def delete_dataset(
        dataset_id: str,
        request: Request,
        current_user: UserModel = Depends(deps.get_current_user)):
    """Delete（logicDelete）"""

    # the: Delete
    dataFileSystem = DataFileSystem.objects(id=dataset_id,
                                            user=current_user.id).first()
    if dataFileSystem is not None:
        try:
            dataFileSystem.deleted = True
            dataFileSystem.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dataFileSystem.save()
        except Exception as e:
            print(e)
            JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                         content={"msg": f"failed to delete: {dataset_id}"})
        else:
            await del_datasets(dataset_id, current_user, request.app.state.use_storage_cumulative)

            JSONResponse(status_code=status.HTTP_200_OK,
                         content={"msg": "success"})
    else:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": "dataset not found"})


@router.get("/checked/name")
async def check_file_path(name: str):
    _double_quotation = '"'
    _single_quotation = "'"
    character = re.findall(f'[/${_double_quotation}{_single_quotation}*<>?\\/|：:]', name)
    if character:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"An invalid character exists in the name< {' '.join(character)} >"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "Successful!"})
