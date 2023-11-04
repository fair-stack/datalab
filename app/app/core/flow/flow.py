# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:flow
@time:2022/11/14
"""
from app.models.mongo import (
    DataFileSystem,
    AnalysisModel2,
    ToolTaskModel,
    UserQuotaModel,
    ExperimentModel,
    UserQuotaStatementModel,
    QuotaStatementEnum,
    ComputingQuotaRuleModel,
)
from app.models.mongo import UserModel
from app.models.mongo.public_data import PublicDataFileModel
import uuid
import json
import asyncio
import toposort
import networkx as nx
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from app.core.config import settings
from app.core.gate import FunctionEvent
from app.utils.common import generate_uuid
from app.utils.statement import create_statement
from app.schemas.tool_source import OutputDataTypes
from app.service.manager.event import EventManager
DEPENDS_FILE = "DEPENDS_FILE"
DATA_FILE = "DATA_FILE"
DEPENDS_MEMORY = "DEPENDS_MEMORY"
DATA_MEMORY = "DATA_MEMORY"
FRONT_DATA = "FRONT_DATA"
DEPENDS_LIST = {DEPENDS_FILE, DEPENDS_MEMORY}


class NodeType(str, Enum):
    task = "task"
    input = "input"
    output = "output"


class InputNode(BaseModel):
    type: NodeType = "input"
    id: str
    name: str
    checked: bool
    to: Optional[list] = []


class OutputNode(BaseModel):
    type: NodeType = "output"
    id: str
    name: str
    checked: bool
    to: Optional[list] = []


class TaskNode(BaseModel):
    type: NodeType = "task"
    id: str
    name: str
    checked: bool
    to: Optional[list] = []
    toolName: str


class DAG:
    def __init__(self, experiments_id):
        self.experiments_id = experiments_id
        self.graph = nx.DiGraph()
        self.task_nodes = {}
        self.data_map = {}

    def from_experiments(self):
        for i in ToolTaskModel.objects(experiment=self.experiments_id, status="Success"):
            task_node = TaskNode(id=i.id,  name=i.name, toolName=i.tool.name, checked=True)
            if i.status == 'Success':
                self.graph.add_node(task_node.id)
                '1e033eaec9d24b7a917ed2af3b'
                self.task_nodes[task_node.id] = task_node
                for _i in i.inputs:
                    data = _i['data']
                    if isinstance(data, dict):
                        if data.get('is_file') or _i.get('type') == 'dir':

                            _file = DataFileSystem.objects(id=data['id']).first()
                            if _file and _file.lab_id == self.experiments_id:
                                data['DAG_TYPE'] = DEPENDS_FILE
                                _map_result = self.data_map.get(_file.id)
                                if _map_result is not None:
                                    output_node = _map_result
                                    output_node.to.append(i.id)
                                else:
                                    output_node = OutputNode(id=_file.id, name=_file.name, to=[i.id], checked=True)
                                self.data_map[output_node.id] = output_node
                                self.graph.add_edge(_file.id, task_node.id)
                            else:
                                print(data["id"], data, data.get('file_extension') == 'datasets')
                                if data.get('file_extension') == 'datasets':
                                    _file = PublicDataFileModel.objects(id=data["id"]).first()
                                data['DAG_TYPE'] = DATA_FILE
                                if _file is None:
                                    _file_id = data['id']
                                else:
                                    _file_id = _file.id
                                input_node = InputNode(id=_file_id,
                                                       name=_i['name'],
                                                       checked=True,
                                                       to=[task_node.id]
                                                       )

                                if self.data_map.get(input_node.id) is not None:
                                    self.data_map.get(input_node.id).to.append(task_node.id)
                                else:
                                    self.data_map[input_node.id] = input_node
                                self.graph.add_node(input_node.id)
                                self.graph.add_edge(input_node.id, task_node.id)
                        elif data.get('is_memory'):
                            data_experiments_id, data_task_id = data['id'].split('_')
                            if data_experiments_id == self.experiments_id:
                                _map_result = self.data_map.get(data['id'])
                                if _map_result is not None:
                                    output_node = _map_result
                                    _map_result.to.append(i.id)
                                else:
                                    output_node = OutputNode(id=data['id'], name=data['name'], to=[i.id], checked=True)
                                data['DAG_TYPE'] = DEPENDS_MEMORY
                                self.data_map[output_node.id] = output_node
                                self.graph.add_edge(data['id'], task_node.id)
                            else:
                                data['DAG_TYPE'] = DATA_MEMORY
                                input_node = InputNode(id=data['id'],
                                                       name=_i.name,
                                                       checked=True,
                                                       to=[task_node.id]
                                                       )
                                self.data_map[input_node.id] = input_node
                                self.graph.add_node(input_node.id)
                                self.graph.add_edge(input_node.id, task_node.id)
                    else:
                        input_node = InputNode(id=str(uuid.uuid4()).replace('-', ''),
                                               name=_i['name'],
                                               checked=True,
                                               to=[task_node.id]
                                               )
                        self.graph.add_node(input_node.id)
                        self.graph.add_edge(input_node.id, task_node.id)
                        self.data_map[input_node.id] = input_node
                for _i in i.outputs:
                    try:
                        data = _i['data']
                        if self.data_map.get(data['id']) is None:
                            output_node = OutputNode(id=data['id'], name=data['name'], checked=True)
                            self.data_map[output_node.id] = output_node
                            self.graph.add_edge(task_node.id, output_node.id)
                            self.task_nodes.get(task_node.id).to.append(output_node.id)
                            self.data_map[output_node.id] = output_node
                    except:
                        if _i['type'] in OutputDataTypes:
                            output_node = OutputNode(id=f"{self.experiments_id}_{task_node.id}", name=_i['name'],
                                                     checked=True)
                            self.data_map[output_node.id] = output_node
                            self.graph.add_edge(task_node.id, output_node.id)
                            self.task_nodes.get(task_node.id).to.append(output_node.id)
                            self.data_map[output_node.id] = output_node

    def from_experiments2(self):
        self.all_inputs = list()
        for i in ToolTaskModel.objects(experiment=self.experiments_id):
            task_node = TaskNode(id=i.id,  name=i.name, toolName=i.tool.name, checked=True)
            if i.status == 'Success':
                self.graph.add_node(task_node.id)
                self.task_nodes[task_node.id] = task_node
                for _i in i.inputs:
                    data = _i['data']
                    if isinstance(data, dict):
                        if data.get('is_file'):
                            _file = DataFileSystem.objects(id=data['id']).first()
                            if _file and _file.lab_id == self.experiments_id:
                                data['DAG_TYPE'] = DEPENDS_FILE
                                _map_result = self.data_map.get(_file.id)
                                if _map_result is not None:
                                    output_node = _map_result
                                    output_node.to.append(i.id)
                                else:
                                    output_node = OutputNode(id=_file.id, name=_file.name, to=[{i.id: _i['name']}], checked=True)
                                self.all_inputs.append(output_node)
                                self.data_map[output_node.id] = output_node
                                self.graph.add_edge(_file.id, task_node.id)
                            else:
                                data['DAG_TYPE'] = DATA_FILE
                                input_node = InputNode(id=_file.id,
                                                       name=_i['name'],
                                                       checked=True,
                                                       to=[{task_node.id: _i['name']}]
                                                       )
                                self.all_inputs.append(input_node)
                                self.data_map[input_node.id] = input_node
                                self.graph.add_node(input_node.id)
                                self.graph.add_edge(input_node.id, task_node.id)
                        elif data.get('is_memory'):
                            data_experiments_id, data_task_id = data['id'].split('_')
                            if data_experiments_id == self.experiments_id:
                                _map_result = self.data_map.get(data['id'])
                                if _map_result is not None:
                                    output_node = _map_result
                                    _map_result.to.append(i.id)
                                else:
                                    output_node = OutputNode(id=data['id'], name=data['name'], to=[{i.id: _i['name']}],
                                                             checked=True)
                                data['DAG_TYPE'] = DEPENDS_MEMORY
                                self.data_map[output_node.id] = output_node
                                self.graph.add_edge(data['id'], task_node.id)
                                self.all_inputs.append(output_node)
                            else:
                                data['DAG_TYPE'] = DATA_MEMORY
                                input_node = InputNode(id=data['id'],
                                                       name=_i.name,
                                                       checked=True,
                                                       to=[{task_node.id: _i['name']}]
                                                       )
                                self.data_map[input_node.id] = input_node
                                self.graph.add_node(input_node.id)
                                self.graph.add_edge(input_node.id, task_node.id)
                                self.all_inputs.append(input_node)
                    else:
                        input_node = InputNode(id=str(uuid.uuid4()).replace('-', ''),
                                               name=_i['name'],
                                               checked=True,
                                               to=[{task_node.id: _i['name']}]
                                               )
                        self.graph.add_node(input_node.id)
                        self.graph.add_edge(input_node.id, task_node.id)
                        self.data_map[input_node.id] = input_node
                        self.all_inputs.append(input_node)

                for _i in i.outputs:
                    try:
                        data = _i['data']
                        if self.data_map.get(data['id']) is None:
                            output_node = OutputNode(id=data['id'], name=data['name'], checked=True)
                            self.data_map[output_node.id] = output_node
                            self.graph.add_edge(task_node.id, output_node.id)
                            self.task_nodes.get(task_node.id).to.append(output_node.id)
                            self.data_map[output_node.id] = output_node
                    except:
                        if _i['type'] == 'int':
                            output_node = OutputNode(id=f"{self.experiments_id}_{task_node.id}", name=_i['name'],
                                                     checked=True)
                            self.data_map[output_node.id] = output_node
                            self.graph.add_edge(task_node.id, output_node.id)
                            self.task_nodes.get(task_node.id).to.append(output_node.id)
                            self.data_map[output_node.id] = output_node

    def front_graph(self):
        graph_data = list()
        for i in nx.algorithms.topological_sort(self.graph):
            _data_node = self.data_map.get(i)
            if _data_node is not None:
                graph_data.append(_data_node.dict())
            else:
                graph_data.append(self.task_nodes.get(i).dict())
        return graph_data


class REDAG:
    def __init__(self, experiments_id, analysis):
        self.all_inputs = list()
        self.experiments_id = experiments_id
        self.graph = nx.DiGraph()
        self.analysis = analysis
        self.nodes = list()

    def from_experiments(self):
        for i in self.analysis.skeleton.experiment_tasks:
            print("ITER NODES", i)
            task_node = TaskNode(id=i['task_id'], name=i['task_name'], toolName=i['tool'], checked=True)
            self.nodes.append(task_node)
            for _i in i['inputs']:
                data = _i['data']
                if isinstance(data, dict):
                    if data.get('is_file'):
                        _file = DataFileSystem.objects(id=data['id']).first()
                        if _file and _file.lab_id == self.experiments_id:
                            data['DAG_TYPE'] = DEPENDS_FILE
                            output_node = OutputNode(id=_file.id, name=_file.name, to=[{task_node.id: _i['name']}],
                                                         checked=True)
                            self.all_inputs.append(output_node)
                        else:
                            data['DAG_TYPE'] = DATA_FILE
                            input_node = InputNode(id=_file.id,
                                                   name=_i['name'],
                                                   checked=True,
                                                   to=[{task_node.id: _i['name']}]
                                                   )
                            self.all_inputs.append(input_node)
                    elif data.get('is_memory'):
                        data_experiments_id, data_task_id = data['id'].split('_')
                        if data_experiments_id == self.experiments_id:
                            output_node = OutputNode(id=data['id'], name=data['name'], to=[{task_node.id: _i['name']}],
                                                         checked=True)
                            data['DAG_TYPE'] = DEPENDS_MEMORY
                            self.all_inputs.append(output_node)
                        else:
                            data['DAG_TYPE'] = DATA_MEMORY
                            input_node = InputNode(id=data['id'],
                                                   name=_i.name,
                                                   checked=True,
                                                   to=[{task_node.id: _i['name']}]
                                                   )
                            self.all_inputs.append(input_node)
                else:
                    input_node = InputNode(id=str(uuid.uuid4()).replace('-', ''),
                                           name=_i['name'],
                                           checked=True,
                                           to=[{task_node.id: _i['name']}]
                                           )
                    self.all_inputs.append(input_node)

    def from_experiments2(self):
        for i in self.analysis.skeleton.inputs:
            task_node = TaskNode(id=i['task_id'], name=i['task_name'], toolName="", checked=True)
            self.nodes.append(task_node)
            _i = i
            # print("inputs", _i)
            data = _i['data']
            if isinstance(data, dict):
                if data.get('is_file'):
                    _file = DataFileSystem.objects(id=data['id']).first()
                    if _file and _file.lab_id == self.experiments_id:
                        data['DAG_TYPE'] = DEPENDS_FILE
                        output_node = OutputNode(id=i['id'], name=_file.name, to=[{task_node.id: _i['name']}],
                                                 checked=True)
                        self.all_inputs.append(output_node)
                    else:
                        data['DAG_TYPE'] = DATA_FILE
                        input_node = InputNode(id=i['id'],
                                               name=_i['name'],
                                               checked=True,
                                               to=[{task_node.id: _i['name']}]
                                               )
                        self.all_inputs.append(input_node)
                elif data.get('is_memory'):
                    data_experiments_id, data_task_id = data['id'].split('_')
                    if data_experiments_id == self.experiments_id:
                        output_node = OutputNode(id=data['id'], name=data['name'],
                                                 to=[{task_node.id: _i['name']}],
                                                 checked=True)
                        data['DAG_TYPE'] = DEPENDS_MEMORY
                        self.all_inputs.append(output_node)
                    else:
                        data['DAG_TYPE'] = DATA_MEMORY
                        input_node = InputNode(id=data['id'],
                                               name=_i.name,
                                               checked=True,
                                               to=[{task_node.id: _i['name']}]
                                               )
                        self.all_inputs.append(input_node)
            else:
                input_node = InputNode(id=i['id'],
                                       name=_i['name'],
                                       checked=True,
                                       to=[{task_node.id: _i['name']}]
                                       )
                self.all_inputs.append(input_node)


class Flow:

    def __init__(self, analysis: AnalysisModel2, outer_input: dict, user, publisher):
        self.analysis = analysis
        self.dag = analysis.dag
        self.graph = nx.DiGraph()
        self.lab_id = analysis.id
        print("INIT", outer_input)
        self.outer_input = outer_input
        self.user = user
        self.user_id = user.id
        self.publisher = publisher
        self.outputs_point = outer_input.get('outputs_path')
        _map = {}
        self.source_tasks = analysis.skeleton.experiment_tasks

    def tasks(self):
        s = REDAG(self.source_tasks[0]['experiment'], self.analysis)
        s.from_experiments()
        functions = dict()
        unable_functions = set()
        for i in self.analysis.dag:
            if i['type'] == 'task' and i['checked'] is False:
                unable_functions.add(i['id'])
        print("Nodes", s.nodes)
        for i in s.nodes:
            _xml = ToolTaskModel.objects(id=i.id).first().tool
            functions[i.id] = dict()
            functions[i.id]['tool'] = i.toolName
            functions[i.id]['inputs'] = {i['name']: None for i in _xml.inputs}
        for i in s.all_inputs:
            for _to in i.to:
                for _k, _v in _to.items():
                    map_function = functions.get(_k)
                    for _input in map_function['inputs']:
                        if _v == _input:
                            map_function['inputs'][_input] = i.id
        return functions, unable_functions

    async def run(self):
        functions, unable_functions = self.tasks()
        input_map = {}
        for i in self.dag:
            if i['type'] == 'input' or i['type'] == 'output':
                for _t in i['to']:
                    if input_map.get(_t) is None:
                        input_map[_t] = list()
                    input_map[_t].append(i)
        _map = dict()
        for i in self.source_tasks:
            if i['task_id'] not in unable_functions:
                print(functions)
                try:
                    _map_func_inputs = functions[i['task_id']]
                except KeyError:
                    print("KeyError", i, i['task_id'])
                    continue
                self.old_lab_id = i['experiment']
                for _input in i['inputs']:
                    _input_type = _input['type']
                    if _input_type == "file":
                        _file = DataFileSystem.objects(id=_input['data']['id']).first()
                        if _file and _file.lab_id == i['experiment']:
                            if _map.get(_file.task_id) is None:
                                _map[_file.task_id] = set()
                            _map[_file.task_id].add(i['task_id'])
                    elif _input_type == "object":
                        data_experiments_id, data_task_id = _input['data']['id'].split('_')
                        if data_experiments_id == i['experiment']:
                            if _map.get(data_task_id) is None:
                                _map[data_task_id] = set()
                            _map[data_task_id].add(i['task_id'])
                    for _mfi_k, _mfi_v in _map_func_inputs['inputs'].items():
                        if _mfi_v is None and _mfi_k == _input['name']:
                            try:
                                functions[i['task_id']]['inputs'][_mfi_k] = _input['id']
                            except:
                                functions[i['task_id']]['inputs'][_mfi_k] = _input['data']['id']
                if _map.get(i['task_id']) is None:
                    _map[i['task_id']] = set()

        _steps = list(toposort.toposort(_map))
        _old_id = dict()
        _steps.reverse()
        _all_task_id = list()
        await self.publisher.set(self.analysis.id + "-stage", json.dumps(_all_task_id, ensure_ascii=False))
        # try:
        for i in _steps:
            for task in i:
                if task not in unable_functions:
                    _task_id = generate_uuid()
                    _params = {"task_id": _task_id,
                               "lab_id": self.lab_id,
                               }
                    _all_task_id.append(_task_id)
                    _old_id[self.old_lab_id + "_" + task] = self.lab_id + "_" + _task_id
                    print("OLD_ID", _old_id)
                    if functions.get(task) is not None:
                        for _k, _v in functions[task]['inputs'].items():
                            _values = self.outer_input.get(_v)
                            print(_k, _v, _values)
                            if _values is not None:
                                _params[_k] = _values
                            else:
                                _params[_k] = {'id': _old_id.get(_v)}
                    function_name = ToolTaskModel.objects(id=task).first().tool.name
                    print("PARAMS", _params)

                    em = EventManager(function_name, _params, UserModel.objects(id=self.user_id).first())
                    _result = await em.trigger(self.publisher)
                    print(_result)
                    # FunctionEvent(self.user_id, function_name, self.outputs_point, **_params).reaction("analysis")
                    await self.publisher.set(self.lab_id, "Pending")
                    while True:
                        print(f"TASK ID---> {_task_id}")
                        status_set = await self.publisher.get(_task_id+'-task')
                        if status_set == settings.COMPUTING_SUCCESS:
                            break
                        elif settings.COMPUTING_FAILED == status_set:
                            _status = settings.COMPUTING_FAILED
                            break
                        await asyncio.sleep(1.5)
        original_balance = UserQuotaModel.objects(user=self.user_id).first().balance
        balance = 0
        cpu_nums = 0
        mermory_nums = 0
        computing_quota = ComputingQuotaRuleModel.objects.first()
        # DAG TOP SORT
        for _ in _all_task_id:
            print(f"TASK ID ----> {_}")
            result_use_resource = await self.publisher.get(f"{_}-resource")
            if result_use_resource is None:
                cpu_quota = computing_quota.cpu_quota
                memory_quota = computing_quota.memory_quota
            else:
                result_use_resource = json.loads(result_use_resource)
                cpu_used = [_ for _ in result_use_resource['cpu_used_list']]
                memory_used = [_ for _ in result_use_resource['memory_percent_list']]
                if len(cpu_used) < 60:
                    cpu_nums += 1
                    cpu_quota = computing_quota.cpu_quota
                else:
                    cpu_quota = [_*computing_quota.cpu_quota for _ in cpu_used]
                if len(memory_used) < 60:
                    memory_quota = computing_quota.memory_quota
                    mermory_nums += 1
                else:
                    memory_quota = [_*computing_quota.memory_quota for _ in memory_used]
            _balance = cpu_quota + memory_quota
            if isinstance(_balance, list):
                try:
                    _balance = sum(_balance)
                except:
                    _balance = 11.3
            balance += _balance
        await create_statement(original_balance-balance, original_balance, self.user, self.user,
                               QuotaStatementEnum.analysis, event=self.analysis)
        UserQuotaModel.objects(user=self.user).first().update(balance=original_balance-balance)
        print(f"FLOW Success {self.lab_id}")
        self.analysis.update(state="COMPLETED")
        await self.publisher.set(self.lab_id, "Success")
        # except Exception as e:
        #     print(e)
        #     self.analysis.update(state="FAILED")



