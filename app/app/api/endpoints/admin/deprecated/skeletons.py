"""
Deprecated:
Analysis tools
"""
import time
from datetime import datetime
from typing import Union, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api import deps
from app.forms.deprecated import SkeletonAdminUpdateForm
from app.models.mongo import (
    AuditRecordsModel,
    SkeletonCategoryModel,
    UserModel,
)
from app.models.mongo.deprecated import SkeletonModel
from app.usecases.deprecated import skeletons_usecase
from app.utils.common import convert_mongo_document_to_data, generate_uuid
from app.utils.msg_util import creat_message

router = APIRouter()


@router.post("/categories/",
             summary="Tool category creation")
def create_skeleton_category(
        name: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param name:
    :param current_user:
    :return:
    """
    if not isinstance(name, str):
        JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                     content={"msg": "invalid name format"})
    name = name.strip()
    if not name:
        JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                     content={"msg": "invalid name"})

    category = SkeletonCategoryModel.objects(name=name).first()
    if category:
        JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                     content={"msg": "category with name `{name}` already exist"})
    else:
        category = SkeletonCategoryModel(
            id=generate_uuid(length=26),
            user=current_user,
            name=name
        )
        category.save()

    return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})


@router.get("/categories/",
            summary="Tool category list")
def read_skeleton_categories(
        page: int = 0,
        size: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param page:
    :param size:
    :param current_user:
    :return:
    """

    skip = page * size

    data = []
    #
    total = SkeletonCategoryModel.objects.count()
    categories = SkeletonCategoryModel.objects.all()[skip: skip + size]
    if categories:
        for category in categories:
            category_data = convert_mongo_document_to_data(category)
            # Author Information
            try:
                category_data["user_name"] = category.user.name
            except Exception as e:
                category_data["user_name"] = ''
            #
            data.append(category_data)
    #
    content = {
        "msg": "success",
        "total": total,
        "data": data
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(content))


@router.put("/categories/{category_id}",
            summary="Tool classification update")
async def update_skeleton_category(
        category_id: str,
        name: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param category_id:
    :param name:
    :param current_user:
    :return:
    """
    category = SkeletonCategoryModel.objects(id=category_id).first()
    if not category:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Skeleton category not found: {category_id}"})

    if not isinstance(name, str):
        JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                     content={"msg": "invalid name format"})
    name = name.strip()
    if not name:
        JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                     content={"msg": "invalid name"})

    # Other names
    duplicated_category = SkeletonCategoryModel.objects(id__ne=category_id, name=name).first()
    if duplicated_category:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Skeleton category with name `{name}` already exist"})
    else:
        category.update(**{
            'name': name,
            'updated_at': datetime.utcnow()
        })
        category.save()

        return JSONResponse(status_code=status.HTTP_200_OK,
                            content={"msg": "success"})


@router.delete("/categories/{category_id}",
               summary="Tool category Delete")
def delete_skeleton_category(
        category_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param category_id:
    :param name:
    :param current_user:
    :return:
    """
    category = SkeletonCategoryModel.objects(id=category_id).first()
    if not category:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"Skeleton category not found: {category_id}"})
    else:
        # Cascading operations，will nullify Corresponding to Skeleton This field
        category.delete()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})


@router.get("/audit/",
            summary="Analysis tools")
async def read_skeleton_audits(
        background_tasks: BackgroundTasks,
        name: Union[str, None] = None,
        user_name: Union[str, None] = None,
        state: Union[str, None] = None,
        is_online: Union[bool, None] = None,
        page: int = 0,
        size: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param background_tasks:
    :param name:
    :param user_name:
    :param state:
    :param is_online:
    :param page:
    :param size:
    :param current_user:
    :return:
    """
    t0 = time.time()
    code, msg, content = await skeletons_usecase.read_skeletons(
        menu=skeletons_usecase.MENU_ADMIN_SKELETON_AUDIT,
        background_tasks=background_tasks,
        viewer_id=current_user.id,
        only_own=False,  # View all
        name=name,
        user_name=user_name,
        state=state,
        is_online=is_online,
        page=page,
        size=size
    )
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    t1 = time.time()
    print(f'admin.read_skeleton_audits: {t1 - t0}')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.put("/audit/{skeleton_id}",
            summary="Analysis tools")
def put_skeleton_audit(
        skeleton_id: str,
        audit_state: str,
        audit_opinion: Optional[str] = None,
        category_name: Optional[str] = None,
        current_user: UserModel = Depends(deps.get_current_user),
):
    """
    Administrator，Analysis tools（APPROVING），Conduct audit operations：
        - APPROVED
        - DISAPPROVED

    :param skeleton_id:
    :param audit_state:
    :param audit_opinion:
    :param category_name:
    :param current_user:
    :return:
    """

    # SkeletonModel: Unlimited users
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found"})

    # Determine whether the status of being audited is satisfied：
    #   - Not allowed： UNAPPROVED, APPROVED, DISAPPROVED
    #   - allow： APPROVING
    state = skeletonModel.state
    if state != "APPROVING":
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "msg": f"SkeletonModel is not submitted for approving yet, please submit first: `{state}`"})

    # Administrator，There can only be two：
    #   - APPROVED
    #   - DISAPPROVED
    if audit_state not in ("APPROVED", "DISAPPROVED"):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"msg": f"invalid audit state: `{audit_state}`"})
    # If approved,，Automated rollout
    is_online = False
    if audit_state == "APPROVED":
        is_online = True

    # category: Default “Others”
    if not category_name:
        category_name = "Others"
    if not isinstance(category_name, str):
        JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                     content={"msg": "invalid category_name format"})
    category_name = category_name.strip()
    if not category_name:
        JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                     content={"msg": "invalid category_name"})
    # If there is no corresponding classification，Then create a new
    category = SkeletonCategoryModel.objects(name=category_name).first()
    if not category:
        category = SkeletonCategoryModel(
            id=generate_uuid(length=26),
            user=current_user,
            name=category_name
        )
        category.save()
        category.reload()

    # Updating state
    skeletonModel.update(**{
        'state': audit_state,
        'auditor': current_user,
        'audit_opinion': audit_opinion if audit_opinion else None,
        'category': category,
        'is_online': is_online,
        'updated_at': datetime.utcnow()
    })
    skeletonModel.save()
    skeletonModel.reload()

    # Determine whether to update an existing version:
    #   - YES： If the new version review result is APPROVED， Corresponding to Go offline
    #   - NO:   Don't do anything with it
    if audit_state == "APPROVED":
        skeleton_renewed_id = skeletonModel.skeleton_renewed
        if skeleton_renewed_id:
            skeletonModel_renewed = SkeletonModel.objects(id=skeleton_renewed_id).first()
            if skeletonModel_renewed:
                skeletonModel_renewed.update(**{
                    'is_online': False,
                    'updated_at': datetime.utcnow()
                })
                skeletonModel_renewed.save()

    try:
        ar = AuditRecordsModel.objects(
            component=SkeletonModel.objects(id=skeleton_id).first() ,
            audit_type='Tools'
        ).first()
        if ar:
            ar.auditor = current_user
            ar.audit_result = "Approved by review" if audit_state == 'APPROVED' else "Failed to pass the audit"
            ar.audit_info = audit_opinion if audit_opinion else None
            ar.audit_at = datetime.utcnow()
            ar.save()
            ar.reload()
            #
            creat_message(user=current_user, message_base=ar, for_user=True)
        #
        return JSONResponse(status_code=status.HTTP_200_OK, content={"msg": "success"})

    except Exception as e:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": str(e)})


@router.get("/skeletons/",
            summary="Analysis tools")
async def read_skeletons(
        background_tasks: BackgroundTasks,
        name: Union[str, None] = None,
        user_name: Union[str, None] = None,
        state: Union[str, None] = None,
        is_online: Union[bool, None] = None,
        page: int = 0,
        size: int = 10,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param background_tasks:
    :param name:
    :param user_name:
    :param state:
    :param is_online:
    :param page:
    :param size:
    :param current_user:
    :return:
    """
    # t0 = time.time()
    code, msg, content = await skeletons_usecase.read_skeletons(
        menu=skeletons_usecase.MENU_ADMIN_SKELETON,
        background_tasks=background_tasks,
        viewer_id=current_user.id,
        only_own=False,  # View all
        name=name,
        user_name=user_name,
        state=state,
        is_online=is_online,
        page=page,
        size=size
    )
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})

    # t1 = time.time()
    # print(f'admin.read_skeletons: {t1 - t0}')
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(content))


@router.get("/skeletons/{skeleton_id}",
            summary="Analysis tools")
async def read_skeleton(
        skeleton_id: str,
        current_user: UserModel = Depends(deps.get_current_user)
):
    """

    :param skeleton_id:
    :param current_user:
    :return:
    """
    code, msg, data = await skeletons_usecase.read_skeleton(skeleton_id=skeleton_id)
    if code != status.HTTP_200_OK:
        return JSONResponse(status_code=code, content={"msg": msg})
    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(data))


@router.put("/{skeleton_id}",
            summary="Analysis tools")
async def update_skeleton(
        skeleton_id: str,
        update_form: SkeletonAdminUpdateForm = Depends(),
        current_user: UserModel = Depends(deps.get_current_user)
):
    """
    （Administrator）Analysis tools：
        - Go online/Go offline
        - Classification

    :param skeleton_id:
    :param update_form:
    :param current_user:
    :return:
    """

    # SkeletonModel
    skeletonModel = SkeletonModel.objects(id=skeleton_id).first()
    if not skeletonModel:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"msg": f"SkeletonModel not found: {skeleton_id}"})

    # state： Not reviewed: UNAPPROVED / Under review: APPROVING / Approved by review: APPROVED / Failed to pass the audit: DISAPPROVED
    state = skeletonModel.state

    updated = False

    # Cache updates
    cache_updates = dict()

    # Go online/Go offline
    # Judgment Skeleton Go online/Go offline： state=APPROVED
    is_online = update_form.is_online
    if is_online is not None:
        if not isinstance(is_online, bool):
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"invalid is_online: {is_online}"})
        if state != 'APPROVED':
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"SkeletonModel is `{state}`, must be APPROVED for online/offline operation"})
        else:
            # Cache update add
            cache_updates["is_online"] = is_online

            print(f"is_online: {is_online}")
            skeletonModel.is_online = is_online
            updated = True

    # Classification
    category_id = update_form.category
    if category_id:
        category = SkeletonCategoryModel.objects(id=category_id).first()
        if not category:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                content={"msg": f"Skeleton category not found: {category_id}"})
        else:
            # Cache update add
            cache_updates["category"] = category_id
            cache_updates["category_name"] = category.name

            skeletonModel.category = category
            updated = True

    # Update time，And save it
    if updated is True:
        skeletonModel.updated_at = datetime.utcnow()
        skeletonModel.save()

    # # Updating the cache
    # await skeletons_usecase.update_skeleton_cache(
    #     skeleton_id=skeleton_id,
    #     **cache_updates
    # )


    #
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "success"})
