# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:quota_usecase
@time:2023/03/22
"""
from decimal import Decimal
from app.models.mongo import UserQuotaStatementModel,AnalysisModel2, ToolTaskModel, ExperimentModel
from typing import Union


def read_event_quota_used(event: Union[AnalysisModel2, ToolTaskModel, ExperimentModel]):
    quota_event = UserQuotaStatementModel.objects(event=event).first()
    use_quota = abs(float(Decimal(quota_event.use))) if quota_event is not None else 0
    return use_quota

