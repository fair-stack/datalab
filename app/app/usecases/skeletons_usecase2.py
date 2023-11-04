import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Union

import aioredis
from fastapi import status, BackgroundTasks
from mongoengine.queryset.visitor import Q

from app.core.config import settings
from app.models.mongo import (
    AnalysisModel2,
    ExperimentModel,
    SkeletonModel2,
    UserModel,
)
from app.models.mongo.skeleton2 import (
    SKELETON_STATES,
    SKELETON_STATES_NOT_EDITABLE,
    SkeletonCategoryModel,
)
from app.schemas import Skeleton2BasicSchema
from app.utils.common import convert_mongo_document_to_data
from app.utils.constants import (
    CACHE_PREFIX_SKELETON,
    CACHE_PREFIX_ADMIN_SKELETON,
    CACHE_PREFIX_ADMIN_SKELETON_AUDIT,
    MENU_SKELETON,
    MENU_ADMIN_SKELETON,
    MENU_ADMIN_SKELETON_AUDIT,
)
from app.utils.file_util import convert_base64_str_to_bytes

# Various names
# category
CATEGORY_NAME_IF_NOT_FOUND = 'There is no'
CATEGORY_NAME_IF_NO_ID = ''
CATEGORY_NAME_IF_ERROR = 'unknown'
# user
USER_NAME_IF_NOT_FOUND = 'There is no'
USER_NAME_IF_NO_ID = ''
USER_NAME_IF_ERROR = 'unknown'
# auditor
AUDITOR_NAME_IF_NOT_FOUND = 'There is no'
AUDITOR_NAME_IF_NO_ID = ''
AUDITOR_NAME_IF_ERROR = 'unknown'
# experiment
EXPERIMENT_NAME_IF_NOT_FOUND = 'There is no'
EXPERIMENT_NAME_IF_NO_ID = ''
EXPERIMENT_NAME_IF_ERROR = 'unknown'


def norm_skeleton_experiment_tasks_datasets_for_memory_type(dataset_data_list: List[Dict]) -> List[Dict]:
    """
    In-memory data，A query assignment is required task_id, lab_id

    :param dataset_data_list:
    :return:
    """
    for dataset_data in dataset_data_list:
        if (dataset_data.get("is_memory") is True) or (dataset_data.get("mark") == "structure"):
            # In-memory data id = labId_taskId
            dataset_data["lab_id"] = dataset_data.get("id").split("_")[0]
            dataset_data["task_id"] = dataset_data.get("id").split("_")[1]
    return dataset_data_list


async def _read_skeleton_from_mongo(
        menu: str,
        skeleton_id: str
) -> Optional[Dict]:
    """

    :param skeleton_id:
    :return:
    """
    # Analysis tools
    if menu == MENU_SKELETON:
        pop_fields = [
            # "id",
            "skeleton_renewed",
            "skeleton_renewed_origin",
            # "version",
            "version_meaning",
            # "user",
            # "experiment",
            # "name",
            # "description",
            "introduction",
            # "logo",
            "previews",
            "organization",
            "developer",
            "contact_name",
            "contact_email",
            "contact_phone",
            "statement",
            "experiment_tasks",
            "experiment_tasks_datasets",
            "dag",
            "inputs_config",
            "outputs_config",
            "inputs",
            "outputs",
            # "state",
            "auditor",
            "audit_opinion",
            # "category",
            # "is_online",
            # "pageviews",

            # Derived information
            'user_name',
            # 'experiment_name',
            'auditor_name',
            # 'category_name',
            # 'analysis_count',
            # 'user_count',
        ]
    # Managing Configuration-Tool management-All tools
    elif menu == MENU_ADMIN_SKELETON:
        pop_fields = [
            # "id",
            "skeleton_renewed",
            "skeleton_renewed_origin",
            # "version",
            "version_meaning",
            # "user",
            # "experiment",
            # "name",
            # "description",
            "introduction",
            "logo",
            "previews",
            "organization",
            "developer",
            "contact_name",
            "contact_email",
            "contact_phone",
            "statement",
            "experiment_tasks",
            "experiment_tasks_datasets",
            "dag",
            "inputs_config",
            "outputs_config",
            "inputs",
            "outputs",
            # "state",
            # "auditor",
            # "audit_opinion",
            # "category",
            # "is_online",
            # "pageviews",

            # Derived information
            # 'user_name',
            'experiment_name',
            'auditor_name',
            # 'category_name',
            # 'analysis_count',
            # 'user_count',
        ]
    # Managing Configuration-Tool management-Tool audit
    elif menu == MENU_ADMIN_SKELETON_AUDIT:
        pop_fields = [
            # "id",
            "skeleton_renewed",
            "skeleton_renewed_origin",
            # "version",
            "version_meaning",
            # "user",
            "experiment",
            # "name",
            # "description",
            "introduction",
            "logo",
            "previews",
            "organization",
            "developer",
            "contact_name",
            "contact_email",
            "contact_phone",
            "statement",
            "experiment_tasks",
            "experiment_tasks_datasets",
            "dag",
            "inputs_config",
            "outputs_config",
            "inputs",
            "outputs",
            # "state",
            # "auditor",
            # "audit_opinion",
            "category",
            # "is_online",
            "pageviews",

            # Derived information
            # 'user_name',
            'experiment_name',
            # 'auditor_name',
            'category_name',
            'analysis_count',
            'user_count',
        ]
    else:
        pop_fields = [
            'experiment_tasks',
            'experiment_tasks_datasets',
            "dag",
            "inputs",
            "outputs",
        ]

    # Reading data
    skeletonModel = SkeletonModel2.objects(id=skeleton_id) \
        .exclude('experiment_tasks') \
        .exclude('experiment_tasks_datasets') \
        .first()

    skeleton_data = convert_mongo_document_to_data(skeletonModel)
    skeleton_data = Skeleton2BasicSchema(**skeleton_data).dict()

    # logo
    if 'logo' not in pop_fields:
        # logo -> base64
        logo = skeleton_data.get("logo")
        # if logo is not None:
        #     skeleton_data['logo'] = get_img_b64_stream(logo)
        # else:
        #     skeleton_data['logo'] = ''
        skeleton_data['logo'] = convert_base64_str_to_bytes(logo)

    # Class name
    if ('category_name' not in pop_fields) and ('category' not in pop_fields):
        try:
            category_id = skeleton_data.get("category")
            if category_id:
                categoryModel = SkeletonCategoryModel.objects(id=category_id).first()
                if categoryModel:
                    skeleton_data['category_name'] = categoryModel.name
                else:
                    print(f"category_name not found for:{category_id}")
                    skeleton_data['category_name'] = CATEGORY_NAME_IF_NOT_FOUND
            # id Does not exist
            else:
                skeleton_data['category_name'] = CATEGORY_NAME_IF_NO_ID
        except Exception as e:
            print(f"category_name: {e}")
            skeleton_data['category_name'] = CATEGORY_NAME_IF_ERROR

    # Author's name
    if ('user_name' not in pop_fields) and ('user' not in pop_fields):
        try:
            user_id = skeleton_data.get("user")
            if user_id:
                userModel = UserModel.objects(id=user_id).first()
                if userModel:
                    skeleton_data['user_name'] = userModel.name
                else:
                    print(f"user_name not found for:{user_id}")
                    skeleton_data['user_name'] = USER_NAME_IF_NOT_FOUND
            # id Does not exist
            else:
                skeleton_data['user_name'] = USER_NAME_IF_NO_ID
        except Exception as e:
            print(f"user_name: {e}")
            skeleton_data["user_name"] = USER_NAME_IF_ERROR

    # Name of reviewer
    if ('auditor_name' not in pop_fields) and ('auditor' not in pop_fields):
        try:
            auditor_id = skeleton_data.get("auditor")
            if auditor_id:
                userModel = UserModel.objects(id=auditor_id).first()
                if userModel:
                    skeleton_data['auditor_name'] = userModel.name
                else:
                    print(f"auditor_name not found for:{auditor_id}")
                    skeleton_data['auditor_name'] = AUDITOR_NAME_IF_NOT_FOUND
            # id Does not exist
            else:
                skeleton_data['auditor_name'] = AUDITOR_NAME_IF_NO_ID
        except Exception as e:
            print(f"auditor_name: {e}")
            skeleton_data["auditor_name"] = AUDITOR_NAME_IF_ERROR

    #  Source Name of Experiment
    if ("experiment_name" not in pop_fields) and ("experiment" not in pop_fields):
        experiment_id = skeleton_data.get("experiment")
        skeleton_data['experiment_name'] = get_experiment_name_for_skeleton(experiment_id)

    # Number of employees
    if 'user_count' not in pop_fields:
        analyses = AnalysisModel2.objects(
            is_trial=False,
            skeleton=skeleton_id
        ).only("user").all()
        user_count = len(set([a.user for a in analyses]))
        skeleton_data["user_count"] = user_count

    # Number of analysis histories （Test runs are not included）
    if "analysis_count" not in pop_fields:
        analysis_count = AnalysisModel2.objects(
            is_trial=False,
            skeleton=skeleton_id
        ).count()
        skeleton_data["analysis_count"] = analysis_count

    # pop Redundant fields
    if isinstance(skeleton_data, Dict):
        # Waiting for integration pop The field of
        for field in pop_fields:
            skeleton_data.pop(field, None)

    return skeleton_data


async def read_skeleton_cache(
        menu: str,
        skeleton_id: str,
        redis_conn
) -> Dict:
    """
    Read cache，Checking for presence
        - YES： reading，Meanwhile norm The format of the returned data（ReturnThe field of str，Must be changed to correspond to the original type int or bool Etc.），Return
            - Be aware of format conversion：
                - Primitive shaping，str -> int
                - Primitive Boolean，str -> bool
        - NO： Does not exist，Return

    :param menu:
    :param skeleton_id:
    :param redis_conn:
    :return:
    """
    # print('-----------------------------------------')
    # t0 = time.time()

    # cache key
    if menu == MENU_SKELETON:
        cache_key = f'{CACHE_PREFIX_SKELETON}_{skeleton_id}'
    elif menu == MENU_ADMIN_SKELETON:
        cache_key = f'{CACHE_PREFIX_ADMIN_SKELETON}_{skeleton_id}'
    elif menu == MENU_ADMIN_SKELETON_AUDIT:
        cache_key = f'{CACHE_PREFIX_ADMIN_SKELETON_AUDIT}_{skeleton_id}'
    else:
        # Default
        print(f'read_skeleton_cache: unknown menu [{menu}], normed')
        cache_key = f'{CACHE_PREFIX_SKELETON}_{skeleton_id}'

    # Query caching
    if redis_conn:
        # Judgment cache key
        key_exists = await redis_conn.exists(cache_key)
        if key_exists:
            cache_data = await redis_conn.hgetall(name=cache_key)
            # Converting data formats：readingData -> The original data format
            if isinstance(cache_data, dict):
                # Primitive Boolean， str -> bool:
                #   - is_online
                is_online = cache_data.get('is_online')
                if is_online is not None:
                    cache_data['is_online'] = True if is_online in ['True', 'true', '1'] else False

                # Primitive shaping， str -> int:
                #   - pageviews
                #   - user_count
                #   - analysis_count
                # Corresponding menu：Analysis tools， Managing Configuration-All tools
                if menu in [MENU_SKELETON, MENU_ADMIN_SKELETON]:
                    cache_data['pageviews'] = int(cache_data.get("pageviews", 0))
                    cache_data['user_count'] = int(cache_data.get("user_count", 0))
                    cache_data['analysis_count'] = int(cache_data.get("analysis_count", 0))

                # t1 = time.time()
                # print(f'read_skeleton_cache: t1 - t0: {t1 - t0}')
                #
                return cache_data
            else:
                # The format is wrong，Then the query db Data
                print(f"read_skeleton_cache: invalid cache_data type: {cache_data}")
                found_valid_cache = False
        else:
            # Does not exist，Then the query db Data
            print(f"read_skeleton_cache: no cache data for: {cache_key}")
            found_valid_cache = False
    else:
        # Does not exist，Then the query db Data
        print(f"read_skeleton_cache: no cache connection")
        found_valid_cache = False

    # Judgmentisreading
    if found_valid_cache is False:
        print('read_skeleton_cache: cache NOT hit')
        skeleton_data = await _read_skeleton_from_mongo(menu=menu, skeleton_id=skeleton_id)

        # t2 = time.time()
        # print(f'read_skeleton_cache: t2 - t0: {t2 - t0}')
        return skeleton_data


async def _update_skeletons_cache(
        menu: str,
        skeleton_ids: List[str]
):
    """
    Refresh all caches
    - Be aware of format conversion：
        - bool -> int:  true -> 1, false -> 0
        - None -> ''

    :param skeleton_ids:
    :return:
    """

    # print("------------------------")
    # print(f'_update_skeletons_cache: menu: {menu}')
    # t1 = time.time()

    try:
        redis_conn = await aioredis.StrictRedis(host=settings.REDIS_HOST,
                                                port=settings.REDIS_PORT,
                                                db=settings.SKELETON_DATA_CACHE_DB,  # note
                                                encoding="utf-8",
                                                decode_responses=True)  # Set to True，Return dict is str，is bytes

        if redis_conn:
            # for skeletonModel in skeletonModels:
            for skeleton_id in skeleton_ids:
                # readingData
                skeleton_data = await _read_skeleton_from_mongo(menu=menu, skeleton_id=skeleton_id)
                # Judgment
                if (not isinstance(skeleton_data, dict)) or (not skeleton_data):
                    continue

                # Before caching，Format conversion
                #  - bool -> int:  true -> 1, false -> 0
                #  - None -> ''
                for k, v in skeleton_data.items():
                    if isinstance(v, bool):
                        # True -> 1 -> '1'
                        skeleton_data[k] = 1 if v is True else 0
                    elif v is None:
                        skeleton_data[k] = ''

                # refresh
                try:
                    # cache key
                    if menu == MENU_SKELETON:
                        cache_key = f'{CACHE_PREFIX_SKELETON}_{skeleton_id}'
                    elif menu == MENU_ADMIN_SKELETON:
                        cache_key = f'{CACHE_PREFIX_ADMIN_SKELETON}_{skeleton_id}'
                    elif menu == MENU_ADMIN_SKELETON_AUDIT:
                        cache_key = f'{CACHE_PREFIX_ADMIN_SKELETON_AUDIT}_{skeleton_id}'
                    else:
                        # Default
                        print(f'_update_skeletons_cache: unknown menu [{menu}], normed')
                        cache_key = f'{CACHE_PREFIX_SKELETON}_{skeleton_id}'
                    # New/Overlay cache
                    if redis_conn:
                        await redis_conn.hset(name=cache_key, mapping=skeleton_data)
                        # Shut down
                        await redis_conn.close()
                except Exception as e:
                    print(f'e: {e}')
                    continue
    except Exception as e:
        print(f'_update_skeletons_cache: {e}')


    # t2 = time.time()
    # print(f'consume: {t2 - t1}')


async def read_skeletons(
        menu: str,
        background_tasks: BackgroundTasks,
        viewer_id: Union[str, None] = None,
        only_own: bool = True,
        name: Union[str, None] = None,
        user_name: Union[str, None] = None,
        state: Union[str, None] = None,
        category: Union[str, None] = None,
        is_online: Union[bool, None] = None,
        page: int = 0,
        size: int = 10
) -> Tuple[int, str, Optional[Dict]]:
    """
    For：Managing Configuration-Tool management
        - Tool management：
            - All tools
        - Tool audit：
            - Pending review
            - Audit record

    :param category:
    :param menu:
    :param background_tasks:
    :param viewer_id: The viewer's user_id
    :param only_own: isData
    :param name: Analysis tools
    :param user_name: Name of author
    :param state:
    :param is_online:
    :param page:
    :param size:

    :return: [code, msg, content{total:xx, data:[]]
    """
    # print("------------------------")
    # t0 = time.time()

    code = status.HTTP_200_OK
    msg = "success"

    skip = page * size

    # Initialization query
    query = None

    if viewer_id in ["", None]:
        query = Q(is_online=True) & Q(state='APPROVED')
    else:
        # JudgmentisView
        if (only_own is True) and (viewer_id is not None):
            query = Q(user=viewer_id)

        # Name of author
        if user_name:
            creators = UserModel.objects(name__icontains=user_name).all()
            if creators:
                user_ids = [creator.id for creator in creators]
                if query is None:
                    query = Q(user__in=user_ids)
                else:
                    query = query & Q(user__in=user_ids)

        # Audit status
        if state:
            # ",' segmentation，Used to pass multiple values
            if "," in state:
                states = state.split(",")
            else:
                states = [state]
            if query is None:
                query = Q(state__in=states)
            else:
                query = query & Q(state__in=states)

        # Online status
        if isinstance(is_online, bool):
            if is_online is True:
                if query is None:
                    query = Q(is_online=True)
                else:
                    query = query & Q(is_online=True)
            else:
                if query is None:
                    query = Q(is_online__ne=True)
                else:
                    query = query & Q(is_online__ne=True)

    # Analysis tools
    if name:
        if query is None:
            query = Q(name__icontains=name)
        else:
            query = query & Q(name__icontains=name)

    # Categories
    if category:
        if query is None:
            query = Q(category=category)
        else:
            query = query & Q(category=category)

    # counts
    count_all = SkeletonModel2.objects().count()
    count_online = SkeletonModel2.objects(is_online=True).count()
    count_offline = SkeletonModel2.objects(is_online__ne=True).count()

    print(f'query: {query}')
    if query is not None:
        total = SkeletonModel2.objects(query).count()
        skeletonModels = SkeletonModel2.objects(query).order_by("-created_at")[skip: skip + size]
    else:
        total = SkeletonModel2.objects.count()
        # only `id`： Return，To speed up subsequent loops，Otherwise it takes a long time
        skeletonModels = SkeletonModel2.objects.order_by("-created_at").only("id")[skip: skip + size]

    # t1 = time.time()
    # print(f'read_skeletons: t1 - t0: {t1 - t0}')

    # Establishing a cache link
    try:
        redis_conn = await aioredis.StrictRedis(host=settings.REDIS_HOST,
                                                port=settings.REDIS_PORT,
                                                db=settings.SKELETON_DATA_CACHE_DB,  # note
                                                encoding="utf-8",
                                                decode_responses=True)  # Set to True，Return dict is str，is bytes
    except Exception as e:
        print(f'e: {e}')
        redis_conn = None

    # t2 = time.time()
    # print(f'read_skeletons: t2 - t1: {t2 - t1}')

    # serialization
    # Just take id
    skeleton_ids = [s.id for s in skeletonModels]

    # # 3.6015121936798096
    # right skeletonModels ReturnThe field of（See you on）

    if menu not in (MENU_SKELETON, MENU_ADMIN_SKELETON, MENU_ADMIN_SKELETON_AUDIT):
        print(f'unknown menu: {menu}')
        data = []
    else:
        data = await asyncio.gather(*(read_skeleton_cache(menu=menu,
                                                          skeleton_id=_id,
                                                          redis_conn=redis_conn) for _id in skeleton_ids))

    # t3 = time.time()
    # print(f'read_skeletons: t3 - t2: {t3 - t2}')

    # Shut down
    try:
        if redis_conn:
            await redis_conn.close()
    except Exception as e:
        print(f'e: {e}')

    # # refresh skeletonModels right
    background_tasks.add_task(_update_skeletons_cache, menu=menu, skeleton_ids=skeleton_ids)

    # Data
    content = {
        "count_all": count_all,
        "count_online": count_online,
        "count_offline": count_offline,
        "total": total,
        "data": data}

    return code, msg, content


async def read_skeleton(
        skeleton_id: str,
        viewer_id: Union[str, None] = None,
) -> Tuple[int, str, Optional[Dict]]:
    """

    :param skeleton_id:
    :param viewer_id:
    :return:
    """
    code = status.HTTP_200_OK
    msg = "success"
    skeleton_data = None

    # SkeletonModel
    skeletonModel = SkeletonModel2.objects(id=skeleton_id).first()
    if not skeletonModel:
        code = status.HTTP_404_NOT_FOUND
        msg = f"SkeletonModel not found: {skeleton_id}"
        return code, msg, skeleton_data

    skeleton_data = convert_mongo_document_to_data(skeletonModel)
    # print(f"skeleton_data keys: {skeleton_data.keys()}")

    # Class name
    try:
        category_id = skeleton_data.get("category")
        if category_id:
            categoryModel = SkeletonCategoryModel.objects(id=category_id).first()
            if categoryModel:
                skeleton_data['category_name'] = categoryModel.name
            else:
                print(f"category_name not found for:{category_id}")
                skeleton_data['category_name'] = CATEGORY_NAME_IF_NOT_FOUND
        # id Does not exist
        else:
            skeleton_data['category_name'] = CATEGORY_NAME_IF_NO_ID
    except Exception as e:
        print(f"category_name: {e}")
        skeleton_data['category_name'] = CATEGORY_NAME_IF_ERROR

    # Name of experiment
    experiment_id = skeleton_data.get("experiment")
    skeleton_data['experiment_name'] = get_experiment_name_for_skeleton(experiment_id)

    # Author's name
    try:
        user_id = skeleton_data.get("user")
        if user_id:
            userModel = UserModel.objects(id=user_id).first()
            if userModel:
                skeleton_data['user_name'] = userModel.name
            else:
                print(f"user_name not found for:{user_id}")
                skeleton_data['user_name'] = USER_NAME_IF_NOT_FOUND
        # id Does not exist
        else:
            skeleton_data['user_name'] = USER_NAME_IF_NO_ID
    except Exception as e:
        print(f"user_name: {e}")
        skeleton_data["user_name"] = USER_NAME_IF_ERROR

    # Name of reviewer
    try:
        auditor_id = skeleton_data.get("auditor")
        if auditor_id:
            userModel = UserModel.objects(id=auditor_id).first()
            if userModel:
                skeleton_data['auditor_name'] = userModel.name
            else:
                print(f"auditor_name not found for:{auditor_id}")
                skeleton_data['auditor_name'] = AUDITOR_NAME_IF_NOT_FOUND
        # id Does not exist
        else:
            skeleton_data['auditor_name'] = AUDITOR_NAME_IF_NO_ID
    except Exception as e:
        print(f"auditor_name: {e}")
        skeleton_data["auditor_name"] = AUDITOR_NAME_IF_ERROR

    # logo -> base64
    logo = skeleton_data.get("logo")  # path str
    # if logo is not None:
    #     skeleton_data['logo'] = get_img_b64_stream(logo)
    # else:
    #     skeleton_data['logo'] = ''
    skeleton_data['logo'] = convert_base64_str_to_bytes(logo)

    # Number of employees
    # Normal operation
    if skeletonModel.is_online is True:
        analyses = AnalysisModel2.objects(
            is_trial=False,
            skeleton=skeleton_id
        ).only("user").all()
        user_count = len(set([a.user for a in analyses]))
    # Test run
    else:
        user_count = 0
    #
    skeleton_data["user_count"] = user_count

    # Full analysis-quantity
    # Normal operation
    if skeletonModel.is_online is True:
        analysis_count_query = Q(is_trial=False) & Q(skeleton=skeleton_id)
    # Test run
    else:
        analysis_count_query = Q(is_trial=True) & Q(skeleton=skeleton_id)
    #
    analysis_count = AnalysisModel2.objects(analysis_count_query).count()
    skeleton_data["analysis_count"] = analysis_count

    # My analysis-quantity
    # Normal operation
    if skeletonModel.is_online is True:
        # Screening：Based on browsing users id
        if viewer_id not in [None, ""]:
            my_analysis_count = AnalysisModel2.objects(
                is_trial=False,
                skeleton=skeleton_id,
                user=viewer_id
            ).count()
        else:
            my_analysis_count = 0
    # Test run: Full analysisquantity
    else:
        my_analysis_count = analysis_count
    #
    skeleton_data["my_analysis_count"] = my_analysis_count

    # Number of user views：refresh
    #   - skeleton Released online
    #   - Check it out once skeleton Details of，refresh +1
    pageviews = skeletonModel.pageviews or 0
    if skeletonModel.is_online is True:
        pageviews += 1
        # Update
        skeletonModel.update(**{
            'pageviews': pageviews,
            'updated_at': datetime.utcnow()
        })
        skeletonModel.save()
    # Number of views
    skeleton_data["pageviews"] = pageviews

    return code, msg, skeleton_data


async def read_skeletons_aggregates_by_category(
        is_online: Union[bool, None] = None,
        name: Optional[str] = None,
) -> List[Dict]:
    """
    Analysis toolsCategories，statisticsquantity

    :return:
    """
    resp = []

    # Iterate over all category -> category_ids = [xx]
    cateModels = SkeletonCategoryModel.objects.order_by("-num").all()
    categories = list(cateModels)

    for cate in categories:
        query = Q(category=cate.id)
        # is_online
        if isinstance(is_online, bool):
            if is_online is True:
                query = query & Q(is_online=True)
            else:
                query = query & Q(is_online=False)
        # name
        if name is not None:
            query = query & Q(name__icontains=name)
        # statistics
        cate_count = SkeletonModel2.objects(query).count()
        # Filtering
        if cate_count == 0:
            continue
        #
        cate_data = {
            "_id": cate.id,
            "category_name": cate.name,
            # "num": cate.num,
            "count": cate_count
        }
        #
        resp.append(cate_data)

    # allCategories：total
    # is_online
    if isinstance(is_online, bool):
        if is_online is True:
            query = Q(is_online=True)
        else:
            query = Q(is_online__ne=True)
    else:
        query = None
    # name
    if name is not None:
        if query is not None:
            query = query & Q(name__icontains=name)
        else:
            query = Q(name__icontains=name)
    #
    if query is not None:
        total = SkeletonModel2.objects(query).count()
    else:
        total = SkeletonModel2.objects.count()
    # “all“ Rank first
    resp.insert(0, {
        "_id": None,
        "category_name": "all",
        "count": total,
        # "num": None
    })
    #
    return resp


def check_if_skeleton_editable(
        pk: str,
        pk_type: str = 'Skeleton',
) -> Tuple[int, str, Optional[bool]]:
    """
    View Skeleton.state， Judgment skeleton is：
    Skeleton.state:   Not reviewed: UNAPPROVED / Under review: APPROVING / Approved by review: APPROVED / Failed to pass the audit: DISAPPROVED

        - editable：Not reviewed, Failed to pass the audit
        - editable: Under review，Approved by review
    :return:
    """
    code = status.HTTP_200_OK
    msg = "skeleton editable"
    editable = None

    if pk_type == 'Skeleton':
        skeletonModel = SkeletonModel2.objects(id=pk).first()
    # TODO: rm
    # elif pk_type == 'CompoundStep':
    #     compoundStepModel = CompoundStepModel.objects(id=pk).first()
    #     if not compoundStepModel:
    #         code = status.HTTP_404_NOT_FOUND
    #         msg = f"compoundStep `{pk}` not found to locate skeleton"
    #         return code, msg, editable
    #     skeletonModel = compoundStepModel.skeleton
    # elif pk_type == 'CompoundStepElement':
    #     compoundStepElementModel = CompoundStepElementModel.objects(id=pk).first()
    #     if not compoundStepElementModel:
    #         code = status.HTTP_404_NOT_FOUND
    #         msg = f"compoundStepElement `{pk}` not found to locate skeleton"
    #         return code, msg, editable
    #     skeletonModel = compoundStepElementModel.skeleton
    else:
        code = status.HTTP_400_BAD_REQUEST
        msg = f"invalid pk_type `{pk_type}` for locating skeleton"
        return code, msg, editable
    #
    if not skeletonModel:
        code = status.HTTP_404_NOT_FOUND
        msg = "skeleton not found"
        return code, msg, editable
    # state
    state = skeletonModel.state
    if state not in SKELETON_STATES:
        code = status.HTTP_404_NOT_FOUND
        msg = f"invalid skeleton state: {state}"
        return code, msg, editable
    #
    if state in SKELETON_STATES_NOT_EDITABLE:
        msg = f"skeleton not editable: {state}"
        editable = False
    else:
        editable = True
    return code, msg, editable


def get_experiment_name_for_skeleton(
        experiment_id: str
) -> str:
    """
    Name of experiment
    :param experiment_id:
    :return:
    """

    try:
        if experiment_id:
            experimentModel = ExperimentModel.objects(id=experiment_id).first()
            if experimentModel:
                experiment_name = experimentModel.name
            else:
                print(f"experiment_name not found for:{experiment_id}")
                experiment_name = EXPERIMENT_NAME_IF_NOT_FOUND
        # id Does not exist
        else:
            experiment_name = EXPERIMENT_NAME_IF_NO_ID
    except Exception as e:
        print(f"experiment_name: {e}")
        experiment_name = EXPERIMENT_NAME_IF_ERROR
    #
    return experiment_name
