# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:resource
@time:2023/03/06
"""
from app.models.mongo import PlatformResourceModel, StorageResourceAllocatedModel


def platform_storage_balance_allocation(allocated_storage_size: int):
    platform_storage = PlatformResourceModel.objects.first().storage
    _d = StorageResourceAllocatedModel.objects
    total_allocate = _d.sum('allocated_storage_size')
    if (platform_storage - total_allocate) < allocated_storage_size:
        return False
    return True


