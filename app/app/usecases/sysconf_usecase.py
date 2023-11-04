from typing import Optional, Dict

from app.core.config import settings
from app.models.mongo import (
    PlatformModel,
)
from app.utils.common import convert_mongo_document_to_data
from app.utils.file_util import convert_base64_str_to_bytes


def enc(s: str) -> str:
    """
    encryption
    :param s:
    :return:
    """
    k = settings.SECRET_KEY
    encry_str = ""
    for i, j in zip(s, k):
        # iIs a character，jIs the secret key character
        temp = str(ord(i) + ord(j)) + '_'   # encryption = Character ofUnicodecode + Secret keyUnicodecode
        encry_str = encry_str + temp
    return encry_str


def dec(p: str) -> str:
    """
    decryption
    :param p:
    :return:
    """
    k = settings.SECRET_KEY
    dec_str = ""
    for i, j in zip(p.split("_")[:-1], k):
        # i encryption，jIs the secret key character
        temp = chr(int(i) - ord(j))     # decryption = (encryptionUnicodecode - Character ofUnicodecode)A single-byte character
        dec_str = dec_str+temp
    return dec_str


def read_platform() -> Optional[Dict]:
    platform = PlatformModel.objects.first()

    if platform is None:
        return None

    data = convert_mongo_document_to_data(platform)
    # data["logo"] = get_img_b64_stream(data.get("logo"))
    data['logo'] = convert_base64_str_to_bytes(data.get("logo"))

    return data

