# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:fairman_test
@time:2023/01/11
"""
import requests

resp = requests.get('https://market.casdc.cn/api/v2/component?software=DataLab').json()
print(resp['data']['list'])
bucket = resp['data']['list'][0]['minioObject']['Bucket']
key = resp['data']['list'][0]['minioObject']['Key']
download_url = f'https://market.casdc.cn/api/v2/component/{bucket}/{key}'
resp = requests.get(download_url, stream=True)
with open(key, 'wb') as f:
    for _r in resp.iter_content(chunk_size=1024):
        if _r:
            f.write(_r)

if __name__ == '__main__':
    ...
