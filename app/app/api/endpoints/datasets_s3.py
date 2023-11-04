import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Request,
    status,
    UploadFile
)
from fastapi.responses import JSONResponse

from app.api import deps
from app.core.config import settings
from app.models.mongo import UserModel, DataFileSystem
from app.schemas import DatasetV2Schema
from app.usecases import datasets_usecase
from app.utils.common import generate_uuid, convert_mongo_document_to_schema
from app.utils.file_util import chunked_copy, generate_dir
from app.utils.middleware_util import get_s3_client
from app.utils.resource_util import check_storage_resource, cache_cumulative_sum

router = APIRouter()


@router.post("/file/upload",
             summary="Data file upload")
async def upload_dataset_file(
        request: Request,
        files: List[UploadFile],
        current_user: UserModel = Depends(deps.get_current_user)):
    """
    Uploading data files, To the current user bucket Within the：
        - bucket_name = current_user.id
        - Duplicate files，Direct coverage
    """
    # Determining Storage resources
    storage_flag = await check_storage_resource(current_user.id, request.app.state.use_storage_cumulative)
    if storage_flag is False:
        return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            content={"msg": f"Users:{current_user.name}<{current_user.email}>Hello., "
                                            f"You currently have no storage resources available，Please request storage resources or contact the platform administrator!"})
    # get client
    client = get_s3_client()

    # Usersthe bucket Does it exist
    bucket_name = current_user.id
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    print(f'uploading <{len(files)}> files: {[file.filename for file in files]}')
    for file in files:
        print(f'uploading file: {file.filename}')

        filename = file.filename
        file_extension = filename.split(".")[-1] if "." in filename else None

        # Allows uploading files of the same name： It overwrites old data
        #   - After the file with the same name is uploaded successfully，You need the corresponding DataFileSystem.deleted = True  (same user Within the name Unique)
        has_duplicate = False
        objects = list(client.list_objects(
            bucket_name=bucket_name,
            recursive=False
        ))  # Traversal only bucketWithin the，Therefore, recursive=False
        for obj in objects:
            # Simultaneous limitation： Name + Types  (Because bucket)
            if (obj.object_name == filename) and (obj.is_dir is False):
                has_duplicate = True
                print(f"bucket `{bucket_name}` found duplicate object for `{filename}`")
                break

        try:
            # Upload first
            # https://fastapi.tiangolo.com/tutorial/request-files/
            # UploadFile.read(size) is async method:
            #   - inside an async path operation function: contents = await myfile.read()
            #   - inside a normal def path operation function: contents = myfile.file.read()
            result = client.put_object(
                bucket_name=bucket_name,
                object_name=filename,
                data=file.file,
                length=-1,
                content_type="application/octet-stream",
                part_size=10 * 1024 * 1024
            )

            # result: get
            etag = result.etag
            object_name = result.object_name

            # stat: get size
            stat = client.stat_object(bucket_name=bucket_name, object_name=object_name)
            size = stat.size
            await cache_cumulative_sum(current_user.id, size, filename, request.app.state.use_storage_cumulative)
            # Establish Model
            try:
                # DataFileSystem Establish, write db
                DataFileSystem(
                    id=etag,
                    name=filename,
                    is_file=True,
                    is_dir=False,
                    store_name=filename,
                    data_size=size,
                    data_path=filename,
                    user=current_user.id,
                    from_source="UPLOADED",
                    deleted=0,
                    created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    data_type="myData",
                    storage_service="oss",
                    file_extension=file_extension,
                    alias_name=filename,
                    parent="root",
                    child=[],
                    deps=0
                ).save()

            except Exception as e:
                print(e)
                return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    content={"msg": f"failed to save: {filename}"})
        except Exception as e:
            print(e)
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                content={"msg": f"failed to save: {filename}"})
        else:
            # Delete files with the same name DataFileSystem （existence，And not yet deleted）
            if has_duplicate:
                duplicateModel = DataFileSystem.objects(
                    id__ne=etag,
                    user=current_user.id,
                    name=filename,
                    is_file=True,
                    deleted=False,
                    data_type="myData",
                    storage_service="oss"
                ).first()
                if duplicateModel:
                    print(f"deleting duplicate object `{duplicateModel.id}`:`{filename}`")
                    duplicateModel.deleted = True
                    duplicateModel.updated_at = datetime.utcnow()
                    duplicateModel.save()
                    print(f"deleted duplicate object `{duplicateModel.id}`:`{filename}`")

        logging.info(f"uploaded: {filename}")

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
        - （Front-end）Compress folders，The zip is then uploaded
        - willDecompressUsersthe
            - After uploading,，Need to be removed
            - minio Ifexistencefile，theDirect coverage
        - Iterate through the file directory level by level，Checking if is file：
            - YES: Splice path，And then upload it
            - NO： Splice path，Keep iterating, continue
        - Only the folder root write DataFileSystem    （Hierarchical relationship，Can be based on minio the path To iterate through each level）
    """
    # Determining Storage resources
    storage_flag = await check_storage_resource(current_user.id, request.app.state.use_storage_cumulative)
    if storage_flag is False:
        return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            content={"msg": f"Users:{current_user.name}<{current_user.email}>Hello., "
                                            f"You currently have no storage resources available，Please request storage resources or contact the platform administrator!"})
    # bucket_name
    # get client
    client = get_s3_client()

    bucket_name = current_user.id
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # UserstheDoes it exist
    storage_path = Path(settings.BASE_DIR, settings.DATA_PATH, current_user.id)
    if not (storage_path.exists() and storage_path.is_dir()):
        storage_path.mkdir(parents=True)

    # .name Filename，Contains the suffix name，Iftheget
    # .stem Filename，No suffixes
    # .suffix Suffix，For example .txt, .png
    # .parent Parent directory，Equivalent to cd ..

    # Filename: "data/15.blob"
    archive = Path(file.filename).as_posix()
    # If archive thefile "data/15.blob"，You need to become "data.blob"
    print(f"archive original: {archive}")

    # Compressed file format
    archive_suffix = Path(archive).suffix  # includes the leading period. '.blob'
    archive_format = archive_suffix.strip(".")  # Get rid of '.'

    # "data/15.blob" ->  "data/15"  ->  ("data" + ".blob")
    # _archive = archive.strip(archive_suffix)
    _archive = archive.replace(archive_suffix, '')
    archive = _archive.split("/")[0] + archive_suffix
    print(f"archive normed: {archive}")
    print(f'uploading archive: {archive}')

    # Folder name
    # data.blob  ->  data
    unpack = Path(archive).stem  # The final path component, minus its last suffix.

    # archive Storage path
    archive_path = Path(storage_path, archive)
    # unpack Storage path
    unpack_path = Path(storage_path, unpack)

    try:
        # file.file is `file-like` object
        # will archive fileWithin thewritethe ~/store_archive
        # chunked_copy(file.file, archive_path)
        chunked_copy(file.file, archive_path)
        print(f"uploaded archive: {archive}")
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to upload archive: {archive}"})

    # Decompress
    try:
        # Decompress archive_stored file, According to different formats，Use the shutil or zipfile
        # theDecompress，theDecompressthe：
        # Decompress  ~/unpack_stored_path/ the：
        # shutil.unpack_archive the：  ~/unpack_stored_path/<inner_folder>/<content>， Among them <inner_folder> Automatic generation
        # zipfile thethe： ~/unpack_stored_path/<content>； Within the <folder>，Decompress ~/unpack_stored_path/<unpack>
        shutil_supported_unpack_formats = datasets_usecase.get_shutil_supported_unpack_formats(
            with_leading_period=False)
        # Checking whether or not shutil the unpack_formats
        if archive_format in shutil_supported_unpack_formats:
            shutil.unpack_archive(filename=archive_path,
                                  extract_dir=unpack_path)
        else:
            # Use the zipfile processing blob
            with zipfile.ZipFile(archive_path) as z:
                # Within the <folder>，Decompress ~/unpack_stored_path/<unpack>
                _unpack_stored_path = unpack_path.joinpath(unpack)
                if not _unpack_stored_path.exists():
                    _unpack_stored_path.mkdir(parents=True)
                z.extractall(path=_unpack_stored_path)
        # Delete archive
        archive_path.unlink()
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to unpack archive: {archive_path}"})

    # Decompressexistence：
    #  1. shutil.unpack_archive Decompress：    ~/unpack_stored_path/<inner_folder>/<content>
    #  2. zipfile.ZipFile Decompress：          ~/unpack_stored_path/<unpack>/<content>，Among them <unpack> Artificial addition，See you on

    try:
        inner_folder_path = list(unpack_path.iterdir())[0]
        # will   ~/unpack_stored_path/<folder>/<content> Copy to ~/unpack_stored_path/<content>，

        shutil.copytree(src=inner_folder_path,
                        dst=unpack_path,
                        dirs_exist_ok=True
                        )

        # Delete ~/unpack_stored_path/<folder>
        # shutil.rmtree(inner_folder_path)

        # Upload to minio
        # asynchronous
        await datasets_usecase.async_upload_local_directory_to_minio(
            client=get_s3_client(),
            local_path=unpack_path.as_posix(),
            bucket_name=bucket_name,
            minio_path=unpack,
            tasks=[]
        )
        # # blocking
        # datasets_usecase.upload_local_directory_to_minio(
        #     local_path=unpack_path.as_posix(),
        #     bucket_name=bucket_name,
        #     minio_path=unpack
        # )

        # DeleteDecompress，file
        data_size = datasets_usecase.get_total_size_of_local_directory(path=unpack_path)

        # DeleteDecompress

        # print("file", unpack_path.absolute())
        await generate_dir(str(unpack_path), "myData", storage_path=storage_path.__fspath__(),
                           user_id=current_user.id, inc_con=request.app.state.use_storage_cumulative)
        shutil.rmtree(unpack_path)
    except Exception as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": f"failed to upload to minio: {e}"})
    else:
        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success"})

    # # fileEstablish DataFileSystem
    # try:
    #     # Ifexistence DataFileSystem： the deleted = True
    #     duplicateModel = DataFileSystem.objects(
    #         user=current_user.id,
    #         name=unpack,
    #         is_file=False,
    #         deleted=False,
    #         data_type="myData",
    #         storage_service="oss"
    #     ).first()
    #     if duplicateModel:
    #         print(f"deleting duplicate datasetModel `{duplicateModel.id}`:`{unpack}`")
    #         duplicateModel.deleted = True
    #         duplicateModel.updated_at = datetime.utcnow()
    #         duplicateModel.save()
    #         print(f"deleted duplicate datasetModel `{duplicateModel.id}`:`{unpack}`")
    #     # New
    #         dataFileSystem = DataFileSystem(
    #         id=generate_uuid(length=26),
    #         name=unpack,
    #         is_file=False,
    #         is_dir=True,
    #         store_name=unpack,
    #         data_size=data_size,
    #         data_path=unpack,
    #         user=current_user.id,
    #         from_source="UPLOADED",
    #         deleted=0,
    #         created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #         updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #         data_type="myData",
    #         storage_service="oss",
    #         alias_name=unpack,
    #         parent="root",
    #         child=[],   # FIXME:
    #         deps=0
    #     )
    #     dataFileSystem.save()
    #     dataFileSystem.reload()
    #
    #     return JSONResponse(status_code=status.HTTP_200_OK,
    #                         content={"msg": "success"})
    # except Exception as e:
    #     print(e)
    #     return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #                         content={"msg": f"failed to save to model `{unpack}`: {e}"})


@router.get("/",
            summary="Data list")
def read_datasets(
        name: str = None,
        file_extension: str = None,
        deps: int = 0,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    get
    :param name:
    :param file_extension: fileTypes
    :param deps: depth
    :param current_user:
    :return:
    """
    if name is not None and name != "":
        name = name + '/'
    query_ = {k: v for k, v in {"name__contains": name, "file_extension": file_extension}.items() if
              k is not None and k != ''}

    if deps > 0 and name is None:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"msg": "depth"})

    dataset_files = list()
    query_ = {k: v for k, v in query_.items() if v is not None}
    _dfs = DataFileSystem.objects(**query_,
                                  user=current_user.id,
                                  deps=deps,
                                  data_type="myData")
    dataset_files.extend(
        map(
            lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema, user=True, revers_map=['user']),
            _dfs
        )
    )
    parent = None
    if dataset_files:
        parent = dataset_files[0]['parent']
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={'data': dataset_files,
                                 'msg': 'Successful',
                                 'parent': parent})
