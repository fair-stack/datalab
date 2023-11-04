from typing import Optional, Dict

from app.models.mongo import (
    ExperimentUiModel,
    IndexUiModel,
    PlatformModel,
    SkeletonUiModel,
)
from app.utils.common import convert_mongo_document_to_data
from app.utils.file_util import convert_base64_str_to_bytes


def read_platform() -> Optional[Dict]:
    platform = PlatformModel.objects.first()

    if platform is None:
        return None

    data = convert_mongo_document_to_data(platform)
    # data["logo"] = get_img_b64_stream(data.get("logo"))
    data['logo'] = convert_base64_str_to_bytes(data.get("logo"))

    return data


def read_indexui() -> Optional[Dict]:
    indexui = IndexUiModel.objects.first()

    if indexui is None:
        return None

    data = convert_mongo_document_to_data(indexui)
    #
    # if data.get("background") is not None:
    #     data['background'] = get_img_b64_stream(data.get("background"))
    # else:
    #     data['background'] = None
    data['background'] = convert_base64_str_to_bytes(data.get("background"))

    return data


def read_experimentui() -> Optional[Dict]:
    experimentui = ExperimentUiModel.objects.first()

    if experimentui is None:
        return None

    data = convert_mongo_document_to_data(experimentui)
    return data


def read_skeletonui() -> Optional[Dict]:
    skeletonui = SkeletonUiModel.objects.first()

    if skeletonui is None:
        return None

    data = convert_mongo_document_to_data(skeletonui)
    return data
