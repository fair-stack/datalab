import base64
import os
from pathlib import Path
import string
from typing import Tuple

from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.PublicKey import RSA
# from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
from fastapi import status


def check_password_strength(pwd: str,
                            categories_required_minimum=4,
                            chars_required_minimum=8) -> Tuple[int, str, str]:
    """
    Cryptographic elements：
    - Character type：English capital，lowercase，Numbers，Special characters
    - Total number of bits：

    Password strength：
        low：  Type = 1,       quantity = 8
        low：  Type = (1, 3),  quantity >= 8
        high：  Type >= 3,      quantity >= 8

    Reference: https://blog.csdn.net/Fools_______/article/details/111682821

    :param pwd:
    :param categories_required_minimum: Character type
    :param chars_required_minimum: quantity

    :return:    [code, msg, strength_str]
    """

    # Character type
    if categories_required_minimum not in [3, 4]:
        categories_required_minimum = 3

    # quantity
    if (not isinstance(chars_required_minimum, int)) or (chars_required_minimum < 8):
        chars_required_minimum = 8

    digit_count = 0     # Numbers
    lower_count = 0     # Capital letters
    upper_count = 0     # lowercase
    punct_count = 0     # Special characters

    for x in pwd:
        # Numbers
        if x in string.digits:
            digit_count += 1
        # Capital letters
        elif x in string.ascii_lowercase:
            lower_count += 1
        # lowercase
        elif x in string.ascii_uppercase:
            upper_count += 1
        # Special symbols
        elif x in string.punctuation:
            punct_count += 1

    code = status.HTTP_200_OK
    msg = "success"
    strength = ""

    # Character type
    categories_count = int(bool(digit_count)) + int(bool(lower_count)) + int(bool(upper_count)) + int(bool(punct_count))
    if categories_count < categories_required_minimum:
        code = status.HTTP_400_BAD_REQUEST
        msg = f"Must contain at least[{categories_required_minimum}]Class character: English capital，lowercase，Numbers，Special characters"
        return code, msg, strength

    # quantity
    chars_count = digit_count + upper_count + lower_count + punct_count
    if chars_count < chars_required_minimum:
        code = status.HTTP_400_BAD_REQUEST
        msg = f"Must contain at least[{chars_required_minimum}]bytes"
        return code, msg, strength

    # Password strength
    #         low：  Type = 1,       quantity = 8
    #         low：  Type = (1, 3),  quantity >= 8
    #         high：  Type >= 3,      quantity >= 8
    if categories_count <= 1 and chars_count <= 8:
        strength = "weak"
    elif categories_count >= 3 and chars_count >= 8:
        strength = "strong"
    else:
        strength = "medium"
    #
    return code, msg, strength


"""
Asymmetric encryption/decryption 
ref: 
https://blog.csdn.net/u012424148/article/details/109642169
https://zhuanlan.zhihu.com/p/181378111

"""


def generate_rsa_key_pair():
    random_generator = Random.new().read
    rsa = RSA.generate(1024, random_generator)

    # path = settings.PEMS_PATH
    path = Path.cwd().joinpath('pems')
    if not path.exists():
        path.mkdir(parents=True)

    print(f'path: {path}')

    # Generate private keys
    private_key = rsa.exportKey()
    if not path.joinpath('rsa_private.pem').exists():
        with open(path.joinpath('rsa_private.pem'), 'w') as f:
            f.write(private_key.decode('utf-8'))

        # Generating public keys
        public_key = rsa.publickey().exportKey()
        with open(path.joinpath('rsa_public.pem'), 'w') as f:
            f.write(public_key.decode('utf-8'))


def rsa_get_key(key_file: str):
    utils_path = Path(os.path.abspath(__file__)).parent
    pems_path = utils_path.joinpath("pems")
    with open(pems_path.joinpath(key_file), 'r') as f:
        keyData = f.read()
        key = RSA.importKey(keyData)
    return key


def rsa_encrypt(text: str):
    # Importing public keys
    public_key = rsa_get_key('rsa_public.pem')
    cipher = PKCS1_cipher.new(public_key)
    encrypted_text = base64.b64encode(cipher.encrypt(bytes(text.encode('utf-8'))))
    encrypted_text = encrypted_text.decode('utf-8')
    # print(f'encrypted_text: {encrypted_text}')
    return encrypted_text


def rsa_decrypt(text: str):
    # Importing private keys
    private_key = rsa_get_key('rsa_private.pem')
    cipher = PKCS1_cipher.new(private_key)
    # random_generator = Random.new().read
    _text = cipher.decrypt(base64.b64decode(text), None)
    decrypted_text = _text.decode('utf-8')
    # print(f'decrypted_text: {decrypted_text}')
    return decrypted_text


if __name__ == '__main__':
    # generate_rsa_key_pair()
    #
    # a = '1234ABC+'
    # enc = rsa_encrypt(a)
    # print(f'enc: {enc}')

    # a = 'test'
    # enc = rsa_encrypt(a)
    # print(f'enc: {enc}')    # Yw42PoioPXS9ix46zX5/0qguMjY4Z50A3m99modl/LmFbWfYjTwvC46THSe5Btg95ASacg35RrrMj7PLovKNOJM+3ttJfPQSb9p7PPgAMSdWSI3PWV2xT2Lard2njvuwfeUJHk3fkpqMKx4wp3PvpkAMCm4TDKBxHguiSRg7/Bo=

    # b = 'JjGRAj2qLgU7t1Mq337uVQrNrwi/oRQEnv9HAXngubYFVwFfakJfThvRRMhlj5wQS3Bo0jy6F/qZs9e6qX4TI/c7KJSf5Sx/NzviL0SaEWYTqK0KMv6cl25TPiVEDDr4KVomCgvDlOF0kP+PMnBI6aRwc2Uym4k/ZJqT01kqV3E='
    # dec = rsa_decrypt(b)
    # print(f'dec: {dec}')

    # print(check_password_strength('test'))
    rsa_decrypt('hello')
