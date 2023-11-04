import asyncio
import glob
import os
import shutil
from pathlib import Path
from typing import Union, List

from fastapi import Depends
from minio import Minio

from app.core.config import settings
from app.utils.middleware_util import get_s3_client


def get_total_size_of_local_directory(path: Union[str, Path]):
    """
    Calculate the total folder size （Free of symlink）

    :param path:
    :return:
    """
    size = 0

    path = Path(path).resolve()
    if path.is_dir():
        for entry in os.scandir(path):
            if entry.is_dir():
                size += get_total_size_of_local_directory(Path(entry).resolve())
            elif entry.is_file():
                entry_size = entry.stat().st_size   # Byte
                # print(f'file - size:  `{Path(entry).resolve().as_posix()}` -> `{entry_size}`')
                size += entry_size
            else:
                # symlink
                continue
    elif path.is_file():
        file_size = path.stat().st_size
        # print(f'file - size:  `{path.resolve().as_posix()}` -> `{file_size}`')
        size += file_size
    else:
        # Others such as symlink，Not counted against
        pass
    return size


def upload_local_directory_to_minio(
        local_path: str,
        bucket_name: str,
        minio_path: str
):
    """
    The local folder，Upload to minio

    :param local_path:
    :param bucket_name:
    :param minio_path:  in bucket Within the storage path
    :return:
    """
    # It has to be dir Types
    if not os.path.isdir(local_path):
        return None

    # Getting the client
    client = get_s3_client()

    # Iterate over all items in the current path (First floor, recursive=False)： file + dir
    for local_file in glob.glob(local_path + '/**', recursive=False):
        # file It contains the parent path，Such as "a/b.txt"
        # Replace `\` with `/` on Windows
        local_file = local_file.replace(os.sep, "/")

        # Checking if is file：  YES：Upload， NO： iteration
        # dir：iteration
        if os.path.isdir(local_file):
            upload_local_directory_to_minio(
                local_path=local_file,
                bucket_name=bucket_name,
                minio_path=f'{minio_path}/{os.path.basename(local_file)}'
            )
        # file：Upload
        elif os.path.isfile(local_file):
            # local_file Contains the current local_path，I need to get rid of that
            remote_path = os.path.join(minio_path, local_file[1 + len(local_path):])
            # Replace \ with / on Windows
            remote_path = remote_path.replace(os.sep, "/")
            client.fput_object(bucket_name, remote_path, local_file)
        # Types： ignore
        else:
            continue
    return None


async def minio_upload_object(client: Minio, bucket_name, remote_path, local_file):
    client.fput_object(bucket_name, remote_path, local_file)
    return None


async def async_upload_local_directory_to_minio(
        client: Minio,
        local_path: str,
        bucket_name: str,
        minio_path: str,
        tasks: List = []
):
    """
    The local folder，Upload to minio

    :param local_path:
    :param bucket_name:
    :param minio_path:  in bucket Within the storage path
    :param tasks:
    :param client:
    :return:
    """
    # It has to be dir Types
    if tasks is None:
        tasks = []
    if not os.path.isdir(local_path):
        return None

    # # Getting the client
    # client = get_s3_client()

    # Iterate over all items in the current path (First floor, recursive=False)： file + dir
    for local_file in glob.glob(local_path + '/**', recursive=False):
        # file It contains the parent path，Such as "a/b.txt"
        # Replace `\` with `/` on Windows
        local_file = local_file.replace(os.sep, "/")

        # Checking if is file：  YES：Upload， NO： iteration
        # dir：iteration
        if os.path.isdir(local_file):
            await async_upload_local_directory_to_minio(
                client=client,
                local_path=local_file,
                bucket_name=bucket_name,
                minio_path=f'{minio_path}/{os.path.basename(local_file)}',
                tasks=tasks
            )
        # file：Upload
        elif os.path.isfile(local_file):
            # local_file Contains the current local_path，I need to get rid of that
            remote_path = os.path.join(minio_path, local_file[1 + len(local_path):])
            # Replace \ with / on Windows
            remote_path = remote_path.replace(os.sep, "/")
            # client.fput_object(bucket_name, remote_path, local_file)
            tasks.append(
                asyncio.create_task(minio_upload_object(
                    client=client,
                    bucket_name=bucket_name,
                    remote_path=remote_path,
                    local_file=local_file)
                )
            )
        # Types： ignore
        else:
            continue

    # execute
    await asyncio.wait(tasks)

    return None


def get_shutil_supported_unpack_formats(with_leading_period: bool = True):
    """
    shutil.get_unpack_formats(): [
        ('bztar', ['.tar.bz2', '.tbz2'], "bzip2'ed tar-file"),
        ('gztar', ['.tar.gz', '.tgz'], "gzip'ed tar-file"),
        ('tar', ['.tar'], 'uncompressed tar file'),
        ('xztar', ['.tar.xz', '.txz'], "xz'ed tar-file"),
        ('zip', ['.zip'], 'ZIP file')
    ]

    :return: [xx, xx]
    """
    resp = []
    for format_tuple in shutil.get_unpack_formats():
        formats = format_tuple[1]
        resp.extend(formats)
    # Whether to remove the beginning "."
    if with_leading_period is False:
        resp = [f.replace(".", "", 1) for f in resp]
    #
    return resp


def get_display_path(data_path, user_id) -> str:
    """
    Get the presentation path

    "/home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/07122cd333df47cc9122d96929.AuroraPrediction/data/15 - copy"
    Displayed as "AuroraPrediction/data/15 - copy"
    # Processing logic: data_path = <BASE_DIR>/<DATA_PATH>/<user>/<uuid>.data_name/<...>,

    :param data_path:
    :param user_id:
    :return:
    """
    ROOT = f"{settings.BASE_DIR}/{settings.DATA_PATH}/"

    # preprocessing
    data_path = data_path.replace(ROOT, "").replace(f"{user_id}/", "")

    # <uuid>.<data_name>/<..>
    if len(data_path) > 26 and data_path[26] == ".":
        display_path = data_path[27:]
    else:
        display_path = data_path
    #
    return display_path
