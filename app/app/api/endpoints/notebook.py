# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:notebook
@time:2023/02/21
"""
import json
from app.api import deps
from datetime import datetime
from typing import Optional
from fastapi import (
    status,
    APIRouter,
    Depends
)
from app.models.mongo import (
    UserModel,
    NoteBookProjectsModel,
    NoteBookSupportLanguageModel)
from fastapi.responses import JSONResponse, RedirectResponse
from app.utils.common import generate_uuid, convert_mongo_document_to_schema
from app.schemas import NoteBookProjectSchemas
from app.core.config import settings
from app.core.note.note_factory import NoteBookFactory
router = APIRouter()


@router.get('/language', summary="Get the currently supported programming languages")
async def get_language(current_user: UserModel = Depends(deps.get_current_user)):
    _subjects = NoteBookSupportLanguageModel.objects(state=True).all()
    _data = [{"id": _.id, "language": _.language, "version": _.version, "icon": _.icon} for _ in _subjects]
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "data": _data})


@router.get('/subject', summary="Get a list of subject areas")
async def get_subject():
    level_map = json.load(open('subject.json'))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "data": level_map})


@router.post('/project', summary="Create an online programming project")
async def create_project(
        name: str,
        language_id: str,
        subject: Optional[str] = None,
        data_source: Optional[list] = None,
        description: Optional[str] = None,
        current_user: UserModel = Depends(deps.get_current_user)
):
    _language = NoteBookSupportLanguageModel.objects(id=language_id).first()
    if _language is None:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    upstream_id = generate_uuid()
    router_id = generate_uuid()
    NoteBookFactory(router_id).create_notebook()
    router_path = f'/{router_id}'
    NoteBookProjectsModel(id=generate_uuid(),
                          name=name,
                          user=current_user,
                          upstream_id=upstream_id,
                          router_id=router_id,
                          router=router_path,
                          cpu=2,
                          description=description,
                          memory=16,
                          data_source=[],
                          language=language_id,
                          subject=subject,
                          ).save()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.put('/project/{project_id}', summary="Modify the project metadata")
async def update_project_meta(project_id: str,
                              name: Optional[str] = None,
                              description: Optional[str] = None,
                              current_user: UserModel = Depends(deps.get_current_user)
                              ):
    _project = NoteBookProjectsModel.objects(id=project_id, user=current_user).first()
    if _project is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"The project does not exist.，Determine if it is the current user<{current_user.name}>My project"})
    update_params = {k: v for k, v in {"name": name, "description": description} if v is not None}
    update_params['update_at'] = datetime.utcnow()
    _project.update(**update_params)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.delete('/project/{project_id}', summary="Deleting an item")
async def delete_project(project_id: str,
                         current_user: UserModel = Depends(deps.get_current_user)):
    # First change the state offline
    _project = NoteBookProjectsModel.objects(id=project_id, user=current_user).first()
    if _project is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"The project does not exist.，Determine if it is the current user<{current_user.name}>My project"})
    _project.update(deleted=True, delete_at=datetime.utcnow())
    # Asynchronous task erasure Route Deployment Svc
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!"})


@router.get('/projects', summary="Get all the items for the current user")
def projects(page: int = 0,
             size: int = 10,
             project_name: Optional[str] = None,
             order_by: Optional[str] = 'create_at',
             current_user: UserModel = Depends(deps.get_current_user)):
    if size > 100:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": "Spider?"})
    skip = page*size
    if project_name:
        _data = NoteBookProjectsModel.objects(name__contains=project_name,
                                              deleted=False, user=current_user).order_by(f"-{order_by}")
    else:
        _data = NoteBookProjectsModel.objects(deleted=False, user=current_user).order_by(f"-{order_by}")
    total = len(_data)
    _projects = list()
    for _ in _data[skip: skip+size]:
        item = convert_mongo_document_to_schema(_, NoteBookProjectSchemas)
        item['language'] = {"name": _.language.language, "version": _.language.version,
                            "icon": _.language.icon}
        _projects.append(item)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!",
                                 "data": _projects,
                                 "total": total})


@router.get('/redirect/{project_id}', summary="Navigate to the online editor for your project")
def redirect_router_path(project_id: str,
                         current_user: UserModel = Depends(deps.get_current_user)):
    _project = NoteBookProjectsModel.objects(id=project_id, user=current_user, deleted=False).first()
    if _project is None:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"The project does not exist.，Determine if it is the current user<{current_user.name}>My project"})
    redirect_url = settings.NOTEBOOK_GATEWAY_URI.replace(":9080", "/dupyter") + _project.router + f"/lab?token={_project.router_id}"
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Successful!", "data": redirect_url})
