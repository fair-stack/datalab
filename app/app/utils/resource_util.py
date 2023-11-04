# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:resource_util
@time:2022/11/10
"""
import time
import datetime
from fastapi import Request
from app.models.mongo import UserQuotaModel, StorageResourceAllocatedModel


def quota_full(user_id: str) -> bool:
    """
    Check if resources are still available for the current user
    :param user_id: Unique user identification
    :return: A Boolean value indicates whether a resource is still available
    """
    if UserQuotaModel.objects(user=user_id).first().balance <= 0:
        return False
    return True


async def cache_cumulative_sum(key: str, value: int, base_dataset_name: str, redis_conn):
    """
    Cache accumulation counter
    :param key: Unique identification
    :param value: Accumulating numbers
    :param base_dataset_name: Filtering parameters
    :param redis_conn: redisConnection
    """
    count = await redis_conn.get(key)
    _file_key = f"{key}:{base_dataset_name}"

    if not count:
        count = 0
        await redis_conn.set(key, value=count)
    try:
        _his_size = await redis_conn.get(_file_key)
        if _his_size:
            count = int(count) - int(_his_size)
        await redis_conn.set(_file_key, value)
        incr_value = int(count) + value
        await redis_conn.set(key, incr_value)
        return True
    except Exception as e:
        print(e)
        return False


async def cut_user_storage_size(user_id: str, value: int, redis_conn):
    try:
        print(f"cut_user_storage_size -> {user_id}| {value}| {redis_conn}")
        count = await redis_conn.get(user_id)
        print(f"cut_user_storage_size COUNT -> {count}")
        incr_value = int(count) - value
        print(f"cut_user_storage_size incr_value -> {incr_value}")
        await redis_conn.set(user_id, incr_value)
        return True
    except Exception as e:
        print(f"Failed to subtract user storage usage：{e}")
        return False


async def get_cache_cumulative_num(user_id, redis_conn):
    _num = await redis_conn.get(user_id)
    if _num is None:
        _num = 0
    return int(_num)


async def check_storage_resource(user_id: str, redis_conn) -> bool:
    allocated_size = StorageResourceAllocatedModel.objects(allocated_user=user_id).first().allocated_storage_size
    used_size = await get_cache_cumulative_num(user_id, redis_conn)
    if (allocated_size-used_size) > 0:
        return True
    return False
