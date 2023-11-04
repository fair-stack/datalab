from typing import Dict, List, Optional, Union

from mongoengine import Q

from app.models.mongo import ToolsTreeModel, XmlToolSourceModel
from app.schemas import ToolSourceBaseSchema
from app.utils.common import convert_mongo_document_to_data


def get_all_tools_categories() -> List:
    """
    get tools All categories of
    """
    resp = []
    tools = XmlToolSourceModel.objects.only("category")
    for tool in tools:
        # tool: <class 'mongoengine.base.datastructures.BaseList'>
        _data = tool._data
        _category = _data.get("category")
        if _category is not None:
            resp.append(_category)
    # duplicate removal，Sorting
    resp = list(set(resp))
    resp.sort()
    return resp


def iter_get_sub_tools_tree(current_level: int,
                            current_name: str,
                            with_data: bool = False,
                            data_query=None) -> List:
    children = []
    t = ToolsTreeModel.objects(level=current_level, name=current_name).first()
    if t:
        # Note： level + 1
        sub_ts = ToolsTreeModel.objects(level=current_level + 1, parent=current_name).all()
        if sub_ts:
            for sub_t in sub_ts:
                sub = {
                    'level': sub_t.level,
                    'name': sub_t.name,
                    'children': iter_get_sub_tools_tree(current_level=sub_t.level,
                                                        current_name=sub_t.name,
                                                        with_data=with_data,
                                                        data_query=data_query)
                }
                if with_data:
                    tools_data = []
                    # Note： It's the moment level The corresponding name
                    query = Q(category=sub_t.name)
                    if data_query:
                        query = query & data_query
                    tools = XmlToolSourceModel.objects(query).all()
                    for tool in tools:
                        _data = convert_mongo_document_to_data(tool)
                        tools_data.append(ToolSourceBaseSchema(**_data))
                    sub['tools'] = tools_data
                children.append(sub)
    return children


def get_tools_tree_hierarchy(with_data: bool = False,
                             data_query = None) -> List:
    """
    get

    :return: [
        {
            'level': xx,
            'name': xx,
            'children': [
                {
                    'level': yy,
                    'name': yy,
                    'children': []
                }
            ]
        }
    ]
    """
    resp = []
    # Start，from 1 Level directory start，get
    ts_1 = ToolsTreeModel.objects(level=1).all()
    if ts_1:
        for t in ts_1:
            sub = {
                'level': 1,
                'name': t.name,
                'children': iter_get_sub_tools_tree(current_level=1,
                                                    current_name=t.name,
                                                    with_data=with_data,
                                                    data_query=data_query)
            }
            if with_data:
                tools_data = []
                # Note： It's the moment level The corresponding name
                query = Q(category=t.name)
                if data_query:
                    query = query & data_query
                tools = XmlToolSourceModel.objects(query).all()
                for tool in tools:
                    _data = convert_mongo_document_to_data(tool)
                    tools_data.append(ToolSourceBaseSchema(**_data))
                sub['tools'] = tools_data
            resp.append(sub)
    return resp


def read_tools_in_tree_format(state: Optional[Union[bool, str]] = '',
                              audit: str = "Approved by review") -> List:
    """
    Component list:

    :param state:
    :param audit: Approved by review， Pending review, etc
    """
    # all
    if audit in ["", None]:
        query = Q(audit__ne='')
    else:
        query = Q(audit=audit)
    if isinstance(state, bool):
        print(f'status: {state}')
        query = query & Q(status=state)
    resp = get_tools_tree_hierarchy(with_data=True, data_query=query)
    return resp


def read_tool(tool_id: str) -> Optional[Dict]:
    """
    Component Details
    """

    tool = XmlToolSourceModel.objects(id=tool_id).first()
    if tool is None:
        return None
    _data = tool.to_mongo().to_dict()
    _data["id"] = _data.get("_id")
    data = ToolSourceBaseSchema(**_data).dict()
    return data


if __name__ == '__main__':
    from app.db.mongo_util import connect_mongodb

    connect_mongodb()
    data = get_tools_tree_hierarchy()
    print(data)
