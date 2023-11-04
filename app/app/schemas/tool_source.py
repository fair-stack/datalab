from typing import Optional, List, Any
import datetime

from pydantic import BaseModel

ParamTypes = ['boolean', 'dir', 'file', 'multi_select', 'number', 'select', 'text',
              'str', 'object', 'int', 'float', 'list', 'dict', 'set', 'bool', 'tuple', 'datasets', "list[datasets]"]
# Container type supplementary definition
ContainerTypes = ["List[datasets]"]
ParamWithOptionsTypes = ['multi_select', 'select', ]
OptionTypes = ['boolean', 'number', 'text']
RequirementTypes = ['language', 'package', ]
OutputDataTypes = ["dir", "file", "int", "float", "str", "list", "tuple", "bytes", "DataFrame", "dict", 'object']


class Requirement(BaseModel):
    type: str   # default: package, ref: RequirementTypes
    version: str
    value: str


class InputParamOption(BaseModel):
    name: str
    type: str  # OptionTypes
    value: Any


class InputParam(BaseModel):
    """
    name:     Must have，name
    label:    Must have，Explain the name
    type:     Must have，ParamTypes
    format:   Optional，tabular, pdf, csv, ...
    required:  Optional，True/False
    default:  Optional，Default values
    help:     Optional，Dataset missing? See TIP below
    options: Optional, (only ParamWithOptionsTypes existence)
    """
    name: str
    label: str
    type: str   # ParamTypes
    format: Optional[str] = None
    required: Optional[bool] = True
    default: Optional[Any]
    help: Optional[str]
    options: Optional[List[InputParamOption]]
    data: Optional[Any] = None


class OutputData(BaseModel):
    """
    name:     Must have，name
    type:     Must have，OutputDataTypes
    format:   Optional，tabular, pdf, csv, ...
    """
    name: str
    type: str   # OutputDataTypes
    format: Optional[str] = None


class TestInputParam(BaseModel):
    """
    """
    name: str
    value: Any


class TestOutputData(BaseModel):
    name: str
    value: Any


class ToolTest(BaseModel):
    inputs: List[TestInputParam]
    outputs: List[TestOutputData]


class XmlToolSourceSchema(BaseModel):
    # pk
    id: str
    # Storage path dependence
    xml_name: str
    folder_name: str
    folder_path: str
    user_space: Optional[str]
    user: Optional[str]
    # Content fields
    name: str
    version: str
    author: str
    category: str
    description: Optional[str]
    requirements: Optional[List[Requirement]]
    executable_path: Optional[str]
    executable: str
    entrypoint: Optional[str]
    command: str
    inputs: List[InputParam]
    outputs: List[OutputData]
    test: Optional[ToolTest]
    help: Optional[str]
    license: Optional[str]
    link: Optional[str]


class ToolSourceBaseSchema(BaseModel):
    # pk
    id: str
    # Storage path dependence
    folder_name: str
    user_space: Optional[str]
    user: Optional[str]
    # Content fields
    name: str
    version: str
    author: str
    category: str
    description: Optional[str]
    inputs: List[InputParam]
    outputs: List[OutputData]
    help: Optional[str]
    created_at: str
    status: bool
    language: str
    audit: str
    license: Optional[str]
    link: Optional[str]


class ToolSourceMiniSchema(BaseModel):
    # pk
    id: str
    # Content fields
    name: str
    version: str
    author: str
    category: str
    status: bool
    audit: str
