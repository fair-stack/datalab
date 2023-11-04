# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:graph
@time:2023/03/03
"""
# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:flow
@time:2022/11/14
"""
import networkx as nx
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from copy import copy, deepcopy
from collections import OrderedDict, defaultdict
from app.models.mongo import DataFileSystem
from app.models.mongo import ToolTaskModel, ExperimentModel
from app.utils.common import generate_uuid

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
    to: Optional[list] = None


class OutputNode(BaseModel):
    type: NodeType = "output"
    id: str
    name: str
    checked: bool
    to: Optional[list] = None


class TaskNode(BaseModel):
    type: NodeType = "task"
    id: str
    name: str
    checked: bool
    to: Optional[list] = None
    toolName: str


class DAG:

    def __init__(self, experiments_id: str):
        self.graph: Optional[nx.DiGraph] = None
        self.experiments_id: str = experiments_id
        self.node_map: Optional[dict] = None
        self.data_map = dict()
        self.data_map['inputs'] = dict()
        self.data_map['outputs'] = dict()
        self.edges = list()

    def reset_graph(self):
        self.data_map['inputs'] = dict()
        self.data_map['outputs'] = dict()
        self.node_map = dict()
        self.graph = nx.DiGraph()

    def add_node(self, node):
        self.graph.add_node(node)

    def add_edge(self, node, other):
        self.graph.add_edge(node, other)

    def top_sort(self):
        return nx.algorithms.topological_sort(self.graph)

    # def edge_from_data(self, data):
    #     # Whether data is input to a component， Creating dependencies
    #     if self.input_map.get(data['id']):
    #         self.add_edge(data, self.input_map.get(data['id']))
    #     else:
    #         node_id = "FRONT" + generate_uuid()

    def create_data(self, node, data_type):
        if self.node_map[data_type].get(node.id) is not None:
            self.add_edge(node.id,node.id)
        self.data_map[data_type][node.id] = node

    def is_depends(self, data, data_type, task_id):
        node_id = None
        node_name = None
        node_checked = None

        if isinstance(data, dict):
            if data.get('is_file'):
                if DataFileSystem.objects(id=data['id']).first().lab_id == self.experiments_id:
                    data['DAG_TYPE'] = DEPENDS_FILE
                else:
                    data['DAG_TYPE'] = DATA_FILE
            elif data.get('is_memory'):
                data_experiments_id, data_task_id = _i['id'].split('_')
                if data_experiments_id == self.experiments_id:
                    data['DAG_TYPE'] = DEPENDS_MEMORY
                else:
                    data['DAG_TYPE'] = DATA_MEMORY
            else:
                data['DAG_TYPE'] = FRONT_DATA
        self.create_data(data, data_type)
        if data_type == "input":
            node = InputNode()
        else:
            node = OutputNode()
        if data['DAG_TYPE'] in DEPENDS_LIST:
            return True
        else:
            return False

    def from_task_nodes(self):
        """
        The task, input, and output were classified separately by all task records of all experiments.
        :return:
        """
        # It's guaranteed to be a clean graph
        # Add nodes first，If the data appears multiple times, it represents a reference，
        self.reset_graph()
        for i in ToolTaskModel.objects(experiment=self.experiments_id):
            task_node = TaskNode(id=i.id, name=i.name, checked=True if i.status == "Success" else False,
                                 toolName=i.tool.name)
            self.node_map[task_node] = task_node
            self.add_node(task_node)
            for _input in i.inputs:
                _dep = self.is_depends(_input, "inputs")
                if _dep:
                    self.edges.append([()])
                else:
                    self.add_node(InputNode(id=generate_uuid(),
                                            name=_input['name'],
                                            checked=True,
                                            to=[task_node]
                              ))
            for _output in i.outputs:
                _dep = self.is_depends(_output, 'outputs')
