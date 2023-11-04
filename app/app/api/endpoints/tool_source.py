import logging
import os
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    status,
    UploadFile,
)
from fastapi.responses import JSONResponse

from app.api import deps
from app.core.config import settings
from app.models.mongo import UserModel
from app.utils.file_util import chunked_copy, clean_after_fail_parse_tool_zip
from app.utils.tool_util.xml_parser import ToolZipSource

router = APIRouter()

# TODO: how to use namedtuple in response?
# TODO: logging -> configured logger


@router.post("/zipfiles/upload",
             summary="Operator compression package(zipFormat)Upload")
def upload_zipfiles(files: List[UploadFile],
                    current_user: UserModel = Depends(deps.get_current_user)):
    """
    Upload  (Format zip)
    """
    # The storage directory for the user，Plus the user, Used to distinguish
    USER_SPACE = current_user.id if current_user is not None else ""
    USER_ID = current_user.id if current_user is not None else ""

    storage_path = Path(settings.BASE_DIR, settings.TOOL_ZIP_PATH, USER_SPACE)
    if not (storage_path.exists() and storage_path.is_dir()):
        # os.makedirs(storage_path, exist_ok=True)
        storage_path.mkdir(parents=True)

    print(f'uploading <{len(files)}> files: {[file.filename for file in files]}')
    for file in files:
        filename = file.filename
        logging.info(f"file: {filename}")
        # TODO: Whether you need to restrict the format of the archive?
        if not filename.endswith(".zip"):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid file format: {filename}"})
        # Store in a directory
        dest_path = Path(storage_path, filename)
        # Check if a file with the same name exists：Upload  TODO: Handling homonyms，Different content situations?
        if dest_path.exists() and dest_path.is_file():
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"file already exist: {filename}"})
        # file.file is `file-like` object
        chunked_copy(file.file, dest_path)
        logging.info(f"uploaded: {filename}")
        # Start parsing
        try:
            extractResult = ToolZipSource(zip_name=filename,
                                          user_space=USER_SPACE,
                                          user_id=USER_ID).extract_xml_tool_source()
            # Check that parsing is normal.
            if extractResult.code != 0:
                # Delete extra files and folders
                try:
                    clean_after_fail_parse_tool_zip(zipfile_name=filename,
                                                    user_space=USER_SPACE)
                except Exception as e:
                    logging.warning(e)
                finally:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"code": extractResult.code,
                                                 "msg": extractResult.msg,
                                                 "data": extractResult.data})
            # Getting extract data
            xmlToolSource = extractResult.data

            # Deposit in db
            parseResult = xmlToolSource.save_to_db()
            if parseResult.code != 0:
                # Delete extra files and folders
                try:
                    clean_after_fail_parse_tool_zip(zipfile_name=filename,
                                                    user_space=USER_SPACE)
                except Exception as e:
                    logging.warning(e)
                finally:
                    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                        content={"code": parseResult.code,
                                                 "msg": parseResult.msg,
                                                 "data": parseResult.data})
        except Exception as e:
            logging.warning(e)
            # Delete extra files and folders
            try:
                clean_after_fail_parse_tool_zip(zipfile_name=filename,
                                                user_space=USER_SPACE)
            except Exception as e:
                logging.warning(e)
            finally:
                JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                             content={"msg": f"file failed to parse: {filename}"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})
