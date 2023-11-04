# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab-getway
@module:handler
@time:2022/09/19
"""
from PIL import Image


def main(input_file: str, output_file: str):
    image_file = Image.open(input_file)
    image_file = image_file.convert('L')
    image_file.save(output_file)


if __name__ == '__main__':
    main('a.png', 'c.png')
