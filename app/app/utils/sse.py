# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:sse
@time:2023/07/21
"""
from typing import Iterable, Iterator


async def event_generator(data):
    index = 0
    while True:
        index += 1
        if await request.is_disconnected():
            break
        # The test takes random data，Take one random number at a time
        if count := new_count():
            yield {'data': count}

        await asyncio.sleep(1)

if __name__ == '__main__':
    ...
