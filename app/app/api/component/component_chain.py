# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:component_chain
@time:2022/11/12
"""
import json
import pickle
import asyncio
from fastapi.responses import JSONResponse
from minio import S3Error
from fastapi.websockets import WebSocket
from fastapi import (
    APIRouter,
    status,
    Depends,
    Request,
    BackgroundTasks
)
from app.api import deps
from app.models.mongo import (
    UserModel,
    DataFileSystem,
    AnalysisModel2,
    UserQuotaModel,
    UserQuotaStatementModel,
    StorageResourceAllocatedModel,
)
# from app.core.flow.steps import LabStep
from app.core.config import settings
from app.utils.common import convert_mongo_document_to_schema
from app.schemas.dataset import DatasetV2Schema
from app.utils.resource_util import quota_full, check_storage_resource
from app.utils.middleware_util import get_s3_client
from app.core.serialize.ptype import frontend_map
from app.core.flow.flow import DAG, Flow
router = APIRouter()


# @router.post('/{step_id}')
# async def component_start(
#         request: Request,
#         step_id: str,
#         data: dict,
#         background_tasks:BackgroundTasks,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#
#     # computing_flag = check_computing_resource(current_user.id)
#     # storage_flag = await check_storage_resource(current_user.id, request.app.state.use_storage_cumulative)
#     # if computing_flag and storage_flag:
#     # if computing_flag and storage_flag:
#     analysis_step = AnalysisStepModel.objects(id=step_id).first()
#     analysis_step_elements = list()
#     for element_id in analysis_step.elements:
#         element_ins = AnalysisStepElementModel.objects(id=element_id,type="TASK").first()
#         if element_ins is not None:
#             analysis_step_elements.append(element_ins)
#     # analysis_step_elements = [AnalysisStepElementModel.objects(id=element_id,type="TASK").first() for
#     #                           element_id in analysis_step.elements]
#
#     source_analysis = analysis_step.analysis
#     sources_steps = source_analysis.steps
#     step_number_in_analysis = sources_steps.index(step_id)
#     # Send to StepsWorker
#     lab_step = LabStep(current_user.id,
#                        analysis_id=source_analysis.id,
#                        step=analysis_step,
#                        step_numbers=step_number_in_analysis,
#                        analysis_step_elements=analysis_step_elements,
#                        elements_param=data,
#                        publisher=request.app.state.task_publisher)
#     lab_step.dag()
#     background_tasks.add_task(lab_step.run)
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})
    # if computing_flag:
    #     return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
    #                         content={"msg": f"Computation scheduling failure! Users:{current_user.name}<{current_user.email}>Hello., "
    #                                         f"You currently have no storage resources available，Interaction analysis is not available at this time，Please request computing resources or contact the platform administrator!"})
    # return JSONResponse(status_code=status.HTTP_411_LENGTH_REQUIRED,
    #                     content={"msg": f"Computation scheduling failure! Users:{current_user.name}<{current_user.email}>Hello., "
    #                                     f"Your current with out using computing resources，Interaction analysis is not available at this time，Please request computing resources or contact the platform administrator!"})


# @router.websocket("/ws/{step_id}")
# async def socket_analysis(websocket: WebSocket, step_id: str):
#     await websocket.accept()
#     while 1:
#         # Collection of component states
#         status_set = set()
#         _status = None
#         all_step_tools = await websocket.app.state.task_publisher.get(f"{step_id}_Monitor")
#         keys = json.loads(all_step_tools)
#         # keys = await websocket.app.state.task_publisher.keys(f"*_{step_id}_*-task")
#         status_set = {await websocket.app.state.task_publisher.get(_) for _ in [f"{i}-task"for i in keys]}
#         # StepAll component states within must all be successful，Only then can the step be considered successful.
#         if len(status_set) == 1 and settings.COMPUTING_SUCCESS in status_set:
#             await websocket.send_json({"status": settings.COMPUTING_SUCCESS})
#         # If any one or more failures appear in the component state set，The step is considered a failure.
#         elif settings.COMPUTING_FAILED in status_set:
#             await websocket.send_json({"status": settings.COMPUTING_FAILED})
#         # Remaining statesStart/PendingThey are all considered to be in operation，Later calculations can be stripped when queues are involvedPendingIt is determined that the task is queued.
#         else:
#             await websocket.send_json({"status": settings.COMPUTING_PENDING})
#         await asyncio.sleep(1)
#     await websocket.close(1000)
#
#
# @router.get('/datasets/{analysis_id}')
# async def components_dataset(analysis_id: str,
#                              step_id: str = None,
#                              name:str = None,
#                              deps: int = 0,
#                              current_user: UserModel = Depends(deps.get_current_user)
#                        ):
#     """
#     Fetching tool data， If you don't givestep_id It is considered that it is necessary to obtain the data for the entire analysis <br>
#     :param analysis_id: Analysisid <br>
#     :param step_id: Stepsid <br>
#     :param deps: File directory hierarchy/depth，Used to iterate into the next level of directory,The default is0，That is, only the first layer is shown. <br>
#     :return:
#     """
#     query_ = dict()
#     if deps > 0 and name is None:
#         return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             content={"msg": "depth"})
#     if name:
#         query_ = {"name": name}
#     dataset_files = list()
#     if step_id is None:
#         files_id_list = [AnalysisStepElementModel.objects(analysis=analysis_id, src_id=_.derived_from_src_id).first().id
#                           for _ in AnalysisStepElementModel.objects(analysis=analysis_id, type__ne="TASK",
#                                          is_selected=True)]
#
#     else:
#         files_id_list = [
#             AnalysisStepElementModel.objects(analysis=analysis_id, src_id=_.derived_from_src_id).first().id
#             for _ in AnalysisStepElementModel.objects(analysis=analysis_id, analysis_step=step_id, type__ne="TASK",
#                                                       is_selected=True)
#                          ]
#         print(files_id_list)
#     if name:
#         _dfs = DataFileSystem.objects(task_id__in= files_id_list, deps=deps).filter(
#             __raw__={'name': {'$regex': f'.*{name}*'}})
#     else:
#         _dfs = DataFileSystem.objects(task_id__in=files_id_list, deps=deps)
#     for _ in _dfs:
#         print(_.id, _.name, _.to_mongo().to_dict())
#     dataset_files.extend(
#         map(
#             lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema, user=True, revers_map=['user']),
#             _dfs
#         )
#     )
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={
#                             'data': dataset_files,
#                             'msg': 'Successful'
#                         }
#                         )

# @router.post('/{step_id}')
# async def component_start(
#         request: Request,
#         step_id: str,
#         data: dict,
#         background_tasks: BackgroundTasks,
#         current_user: UserModel = Depends(deps.get_current_user)
# ):
#
#     quota_full = check_computing_resource(current_user.id)
#     storage_full = await check_storage_resource(current_user.id, request.app.state.use_storage_cumulative)
#     if not quota_full:
#         return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
#                             content={"msg": f"Computation scheduling failure! Users:{current_user.name}<{current_user.email}>Hello., "
#                                             f"You currently have no quota available，Interaction analysis is not available at this time，Please contact the platform administrator for more quotas!"})
#     if storage_full:
#         return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
#                             content={"msg": f"Computation scheduling failure! Users:{current_user.name}<{current_user.email}>Hello., "
#                                             f"You currently have no storage resources available，Interaction analysis is not available at this time，Redeem the storage resources by quota（）Or contact the platform administrator!"})
#     analysis_step = AnalysisStepModel.objects(id=step_id).first()
#     analysis_step_elements = list()
#     for element_id in analysis_step.elements:
#         element_ins = AnalysisStepElementModel.objects(id=element_id,type="TASK").first()
#         if element_ins is not None:
#             analysis_step_elements.append(element_ins)
#     # analysis_step_elements = [AnalysisStepElementModel.objects(id=element_id,type="TASK").first() for
#     #                           element_id in analysis_step.elements]
#
#     source_analysis = analysis_step.analysis
#     sources_steps = source_analysis.steps
#     step_number_in_analysis = sources_steps.index(step_id)
#     # Send to StepsWorker
#     lab_step = LabStep(current_user.id,
#                        analysis_id=source_analysis.id,
#                        step=analysis_step,
#                        step_numbers=step_number_in_analysis,
#                        analysis_step_elements=analysis_step_elements,
#                        elements_param=data,
#                        publisher=request.app.state.task_publisher)
#     lab_step.dag()
#     background_tasks.add_task(lab_step.run)
#     return JSONResponse(status_code=status.HTTP_200_OK,
#                         content={"msg": "Success"})


@router.get('/dag/{experiments_id}')
async def components_dataset(experiments_id: str

                       ):
    _dag = DAG(experiments_id)
    _dag.from_experiments()
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _dag.front_graph()})


@router.post('/{analysis_id}')
async def component_start(
        request: Request,
        analysis_id: str,
        data: dict,
        background_tasks: BackgroundTasks,
        current_user: UserModel = Depends(deps.get_current_user)
):
    user_quota_full = quota_full(current_user.id)
    storage_full = await check_storage_resource(current_user.id, request.app.state.use_storage_cumulative)
    if not user_quota_full:
        return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            content={"msg": f"Computation scheduling failure! Users:{current_user.name}<{current_user.email}>Hello., "
                                            f"You currently have no quota available，Interaction analysis is not available at this time，Please contact the platform administrator for more quotas!"})
    if not storage_full:
        return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            content={"msg": f"Computation scheduling failure! Users:{current_user.name}<{current_user.email}>Hello., "
                                            f"You currently have no storage resources available，Interaction analysis is not available at this time，Redeem the storage resources by quota（）Or contact the platform administrator!"})
    _analysis = AnalysisModel2.objects(id=analysis_id).first()
    if _analysis is None:
        return JSONResponse(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            content={"msg": f"Computation scheduling failure，Analysis<{analysis_id}>Metadata loss！"})
    await request.app.state.task_publisher.set(analysis_id, "Start")
    _analysis.update(state="INCOMPLETED")
    background_tasks.add_task(Flow(_analysis, data, current_user, request.app.state.task_publisher).run)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"msg": "Success"})


@router.websocket("/ws/{analysis_id}")
async def socket_analysis(websocket: WebSocket, analysis_id: str):
    await websocket.accept()
    while 1:
        _status = await websocket.app.state.task_publisher.get(analysis_id)
        _all_task = json.loads(await websocket.app.state.task_publisher.get(analysis_id + '-stage'))
        _msg = list()
        for _task in _all_task:
            _msg.extend(await websocket.app.state.task_publisher.lrange(_task, 0, -1))
        if _status == settings.COMPUTING_SUCCESS:
            await websocket.send_json({"status": settings.COMPUTING_SUCCESS, "msg": _msg})
            break
        elif _status == settings.COMPUTING_PENDING:
            await websocket.send_json({"status": settings.COMPUTING_PENDING, "msg": _msg})
        elif _status == settings.COMPUTING_FAILED:
            await websocket.send_json({"status": settings.COMPUTING_FAILED, "msg": _msg})
        await asyncio.sleep(1)
    await websocket.close(1000)


@router.get('/results/{analysis_id}')
async def get_analysis_result(
        analysis_id: str,
        current_user: UserModel = Depends(deps.get_current_user)):
    client = get_s3_client()
    _d = DataFileSystem.objects(lab_id=analysis_id,deps=0)
    _files = list(map(lambda x: convert_mongo_document_to_schema(x, DatasetV2Schema, user=True, revers_map=['user']), _d))
    _structure = list()
    try:
        for _ in client.list_objects(analysis_id):
            try:
                _io = client.get_object(analysis_id, _.object_name + "labVenvData.pkl")
            except S3Error:
                pass
            try:
                _object = pickle.load(_io)
            except Exception as e:
                print(f"Serialization exception {e}: {analysis_id}/{_.object_name}")
                _object = None
            _virtual = frontend_map(_object, f"{analysis_id}_{_.object_name.replace('/', '')}")
            _virtual['is_memory'] = True
            _files.append(_virtual)

    except S3Error:
        pass
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content={"data": _files,
                                 "msg": "Successful!"})
