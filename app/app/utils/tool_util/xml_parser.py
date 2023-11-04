"""
Analytic operator XML
"""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Union

from app.core.config import settings
from app.models.mongo import XmlToolSourceModel
from app.models.mongo.tool_source import (
    XmlToolSourceReqFields,
    XmlToolSourceInputsReqFields,
    XmlToolSourceOutputsReqFields,
)
from app.results import (
    ToolSourceExtractResult,
    ToolSourceExtractResult_0,
    ToolSourceExtractResult_1001,
    ToolSourceExtractResult_1005,
    ToolSourceExtractResult_1002,
    ToolSourceExtractResult_1003,
    ToolSourceExtractResult_1004,
    ToolSourceParseResult,
    ToolSourceParseResult_0,
    ToolSourceParseResult_2001,
    ToolSourceParseResult_2002,
    ToolSourceParseResult_2003,
    ToolSourceParseResult_2004,
    ToolSourceParseResult_2005,
    ToolSourceParseResult_2006,
    ToolSourceParseResult_2007,
    ToolSourceParseResult_2008,
    ToolSourceParseResult_2009,
)
from app.schemas.tool_source import (
    OptionTypes,
    OutputDataTypes,
    ParamTypes,
    ParamWithOptionsTypes,
    RequirementTypes,
)

from app.utils.common import generate_uuid


# TODO: print -> logger


class XmlToolSource:

    def __init__(self,
                 folder_name: str,
                 tool_path: str = str(Path(settings.BASE_DIR, settings.TOOL_PATH)),
                 user_space: Optional[str] = "",
                 user_id: Optional[str] = ""
                 ):
        """"
        """
        # Must have the same name prefix: xml and folder
        xml_name = f'{folder_name}.xml'
        # assignment
        self.xml_name = xml_name
        self.folder_name = folder_name
        self.tool_path = tool_path
        self.user_space = user_space
        self.user_id = user_id
        # Derived fields
        self.folder_path = Path(tool_path, user_space, folder_name)
        self.source_path = Path(tool_path, user_space, folder_name, xml_name)

    @property
    def xml_tree(self):
        tree = None
        # Judging existence
        if self.source_path.exists() and self.source_path.is_file():
            try:
                tree = ET.parse(self.source_path)
            except Exception as e:
                print(e)
        return tree

    @property
    def root(self):
        tree = self.xml_tree
        if tree is not None:
            return self.xml_tree.getroot()
        return None

    def parse_name(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("name") is not None:
            name_ele = root.find("name")
            name = name_ele.text.strip() if (name_ele.text is not None) else None
            return name
        else:
            return None

    def parse_version(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("version") is not None:
            version_ele = root.find("version")
            version = version_ele.text.strip() if (version_ele.text is not None) else None
            return version
        else:
            return None

    def parse_author(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("author") is not None:
            author_ele = root.find("author")
            author = author_ele.text.strip() if (author_ele.text is not None) else None
            return author
        else:
            return None

    def parse_categories(self) -> Optional[List]:
        root = self.root
        if root is None:
            return None
        if root.find("categories") is not None:
            categories_ele = root.find("categories")
            category_eles = list(categories_ele)
            if len(category_eles) > 0:
                resp_set = set()
                for category_ele in category_eles:
                    text = category_ele.text.strip()
                    resp_set.add(text)
                return list(resp_set)
            else:
                return None
        else:
            return None

    def parse_category(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("category") is not None:
            category_ele = root.find("category")
            category = category_ele.text.strip() if (category_ele.text is not None) else None
            return category
        else:
            return None

    def parse_description(self):
        root = self.root
        if root is None:
            return None
        if root.find("description") is not None:
            description_ele = root.find("description")
            description = description_ele.text.strip() if (description_ele.text is not None) else None
            return description
        else:
            return None

    def parse_requirements(self) -> Optional[List[Dict]]:
        root = self.root
        if root is None:
            return None
        if root.find("requirements") is not None:
            requirements_ele = root.find("requirements")
            requirement_eles = list(requirements_ele)
            if len(requirement_eles) > 0:
                resp = list()
                for requirement_ele in requirement_eles:
                    r_dict = dict()
                    attrs = requirement_ele.attrib
                    r_dict["type"] = attrs.get("type")
                    r_dict["version"] = attrs.get("version")
                    r_dict["value"] = requirement_ele.text.strip() if (requirement_ele.text is not None) else None
                    if attrs.get("type") == "language":
                        self.language = r_dict["value"]
                    resp.append(r_dict)
                return resp
            else:
                return None
        else:
            return None

    def parse_executable_path(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("executable_path") is not None:
            executable_path_ele = root.find("executable_path")
            executable_path = executable_path_ele.text.strip() if (executable_path_ele.text is not None) else None
            return executable_path
        else:
            return None

    def parse_executable(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("executable") is not None:
            executable_ele = root.find("executable")
            executable = executable_ele.text.strip() if (executable_ele.text is not None) else None
            return executable
        else:
            return None

    def parse_entrypoint(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("entrypoint") is not None:
            entrypoint_ele = root.find("entrypoint")
            entrypoint = entrypoint_ele.text.strip() if (entrypoint_ele.text is not None) else None
            return entrypoint
        else:
            return None

    def parse_command(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("command") is not None:
            command_ele = root.find("command")
            command = command_ele.text.strip() if (command_ele.text is not None) else None
            return command
        else:
            return None

    def parse_inputs(self) -> Optional[List]:
        root = self.root
        if root is None:
            return None
        if root.find("inputs") is not None:
            inputs_ele = root.find("inputs")
            param_eles = list(inputs_ele)  # getchildren was deprecated since 3.4
            resp = list()
            for param_ele in param_eles:
                param_dict = self._parse_input_param(param_ele)
                resp.append(param_dict)
            return resp
        else:
            return None

    def _parse_input_param(self, param_element: ET.Element) -> Dict:
        resp = dict()
        attrs = param_element.attrib
        resp["name"] = attrs.get("name")
        resp["label"] = attrs.get("label")
        _type = attrs.get("type")
        resp["type"] = _type.lower() if isinstance(_type, str) else _type
        resp["format"] = attrs.get("format")
        resp["required"] = attrs.get("required", True)
        resp["default"] = attrs.get("default")
        resp["help"] = attrs.get("help")
        # options
        resp["options"] = self._parse_input_param_options(param_element)
        return resp

    @staticmethod
    def _parse_input_param_options(param_element: ET.Element) -> Optional[List[Dict]]:
        resp = list()
        _type = param_element.attrib.get("type")
        _type = _type.lower() if _type else _type
        if _type in ParamWithOptionsTypes:
            option_eles = list(param_element)
            for option_ele in option_eles:
                s_dict = dict()
                attrs = option_ele.attrib
                s_dict["name"] = attrs.get("name")
                _type = attrs.get("type")
                s_dict["type"] = _type.lower() if isinstance(_type, str) else _type
                s_dict["value"] = option_ele.text.strip() if (option_ele.text is not None) else None
                resp.append(s_dict)
        return resp

    def parse_outputs(self):
        root = self.root
        if root is None:
            return None
        if root.find("outputs") is not None:
            outputs_ele = root.find("outputs")
            data_eles = list(outputs_ele)
            resp = list()
            for data_ele in data_eles:
                data_dict = self._parse_output_data(data_ele)
                resp.append(data_dict)
            return resp
        else:
            return None

    @staticmethod
    def _parse_output_data(data_element: ET.Element) -> Dict:
        resp = dict()
        attrs = data_element.attrib
        resp["name"] = attrs.get("name")
        resp["type"] = attrs.get("type")
        resp["format"] = attrs.get("format")
        return resp

    def parse_test(self) -> Optional[Dict]:
        root = self.root
        if root is None:
            return None
        if root.find("test") is not None:
            test_ele = root.find("test")
            inputs_ele = test_ele.find("inputs")
            outputs_ele = test_ele.find("outputs")
            resp = dict()
            resp["inputs"] = [self._parse_test_input_param(input_ele) for input_ele in inputs_ele]
            resp["outputs"] = [self._parse_test_output_data(output_ele) for output_ele in outputs_ele]
            return resp
        else:
            return None

    @staticmethod
    def _parse_test_input_param(param_element: ET.Element) -> Dict:
        resp = dict()
        attrs = param_element.attrib
        resp["name"] = attrs.get("name")
        resp["value"] = param_element.text.strip() if (param_element.text is not None) else None
        return resp

    @staticmethod
    def _parse_test_output_data(data_element: ET.Element) -> Dict:
        resp = dict()
        attrs = data_element.attrib
        resp["name"] = attrs.get("name")
        resp["value"] = data_element.text.strip() if (data_element.text is not None) else None
        return resp

    def parse_help(self) -> Optional[str]:
        root = self.root
        if root is None:
            return None
        if root.find("help") is not None:
            help_ele = root.find("help")
            _help = help_ele.text.strip() if (help_ele.text is not None) else None
            return _help
        else:
            return None

    def to_dict(self) -> ToolSourceParseResult:
        resp = dict()
        #
        root = self.root
        if root is None:
            return ToolSourceParseResult_2001(msg="ToolSourceParseResult is None")

        # Storage path dependence
        resp["xml_name"] = self.xml_name
        resp["folder_name"] = self.folder_name
        resp["folder_path"] = str(self.folder_path)
        resp["user_space"] = self.user_space
        resp["user"] = self.user_id  # ReferenceField
        # Content fields
        resp["name"] = self.parse_name()
        resp["version"] = self.parse_version()
        resp["author"] = self.parse_author()
        resp["category"] = self.parse_category()
        resp["description"] = self.parse_description()
        resp["requirements"] = self.parse_requirements()
        resp["executable_path"] = self.parse_executable_path()
        resp["executable"] = self.parse_executable()
        resp["entrypoint"] = self.parse_entrypoint()
        resp["command"] = self.parse_command()
        try:
            resp["inputs"] = self.parse_inputs()
        except:
            resp["inputs"] = []
        resp["outputs"] = self.parse_outputs()
        resp["test"] = self.parse_test()
        resp["help"] = self.parse_help()
        resp["language"] = self.language
        resp["status"] = True
        # Determines if required fields are present （Reference to mongo..tool_source.XmlToolSourceReqFields）
        for req_field in XmlToolSourceReqFields:
            if resp.get(req_field) is None:
                return ToolSourceParseResult_2002(msg= f"invalid xml, `req_field is missing: {req_field}", data=resp)
        # Determine the properties of a particular field，Whether the scope requirements are met: requirements / inputs.param / inputs.param.option / outputs.outputdata
        # verification：requirements
        if resp["requirements"] is not None:
            for r_dict in resp["requirements"]:
                _type = r_dict.get("type")
                if _type not in RequirementTypes:
                    return ToolSourceParseResult_2003(msg=f"invalid requirement.type: `{_type}`", data=resp)
        # verification：inputs.param
        if resp["inputs"] is not None:
            for param_dict in resp["inputs"]:
                # Required fields
                for req_field in XmlToolSourceInputsReqFields:
                    if param_dict.get(req_field) is None:
                        return ToolSourceParseResult_2004(msg=f"invalid xml, inputs.param.req_field is missing: {req_field}", data=resp)
                # Judgment param type
                param_type = param_dict.get("type")
                if param_type not in ParamTypes:
                    return ToolSourceParseResult_2005(msg=f"invalid inputs.param.type: {param_type}", data=resp)

                # If param with option，the Judgment option type
                if param_type in ParamWithOptionsTypes:
                    options = param_dict.get("options")
                    # param_type Meet the requirements，But it's missing options
                    if bool(options) is False:
                        return ToolSourceParseResult_2006(msg=f"options are missing for inputs.param.type {param_type}", data=resp)
                    # Judgment option type
                    for option_dict in options:
                        option_type = option_dict.get("type")
                        if option_type not in OptionTypes:
                            return ToolSourceParseResult_2007(msg=f"invalid inputs.param.option.type: {option_type}", data=resp)
        # verification：outputs.outputdata
        if resp["outputs"] is not None:
            for outputdata_dict in resp["outputs"]:
                # Required fields
                for req_field in XmlToolSourceOutputsReqFields:
                    if outputdata_dict.get(req_field) is None:
                        return ToolSourceParseResult_2008(msg=f"invalid xml, outputs.data.req_field is missing: {req_field}", data=resp)
                # Judgment param type
                outputdata_type = outputdata_dict.get("type")
                if outputdata_type not in OutputDataTypes:
                    return ToolSourceParseResult_2005(msg=f"invalid outputs.data.type: {outputdata_type}", data=resp)

        # TODO: verification：test

        return ToolSourceParseResult_0(msg="success", data=resp)

    def save_to_db(self) -> ToolSourceParseResult:
        # Determines if required fields are present （Reference to XmlToolSourceModel）
        parseResult = self.to_dict()
        if parseResult.code != 0:
            return parseResult
        try:
            data = parseResult.data
            document = XmlToolSourceModel(**data,
                                          id=generate_uuid(length=26))
            document = document.save()
            return ToolSourceParseResult_0(msg="success", data=document)
        except Exception as e:
            print(e)
            print(f'failed to save xml to db: {self.xml_name}')
            return ToolSourceParseResult_2009(msg=f"failed to save xml to db: {self.xml_name}")


class ToolZipSource:
    """
    Operator compression package
        Names must be consistent
        <tool>.zip:
            - <tool>.xml
            - <executable>
    """

    def __init__(self,
                 zip_name: str,
                 zip_path: str = str(Path(settings.BASE_DIR, settings.TOOL_ZIP_PATH)),  # Storage directory，exclusive of `zip_name`
                 unzip_path: str = str(Path(settings.BASE_DIR, settings.TOOL_PATH)),  # Unzip the directory
                 user_space: Optional[str] = "",
                 user_id: Optional[str] = ""
                 ):
        self.zip_name = zip_name
        self.zip_path = Path(zip_path, user_space)
        self.unzip_path = Path(unzip_path, user_space)
        self.user_space = user_space
        self.user_id = user_id

    def extract_xml_tool_source(self) -> Union[ToolSourceExtractResult, ToolSourceParseResult]:
        try:
            path = Path(self.zip_path, self.zip_name)
            # Judging existence: source
            if path.exists() and path.is_file():
                # Decompress
                with zipfile.ZipFile(path) as z:
                    z.extractall(self.unzip_path)
                # Extract from：<unzip_path> / <tool_folder> / [tool.xml, tool, test-data]
                base_name = self.zip_name.removesuffix(".zip")
                folder_name = base_name
                xml_name = f"{base_name}.xml"
                # Judgment xml existence
                xml_path = Path(self.unzip_path, folder_name, xml_name)
                if not (xml_path.exists() and xml_path.is_file()):
                    print(f'{xml_path} not exists')
                    # return None
                    return ToolSourceExtractResult_1001(msg=f"xml not exists: {xml_name}")

                # Judgment test-data existence
                # No forced detection for nowtest-datathe
                # test_data_path = Path(self.unzip_path, folder_name, "test-data")
                # if not (test_data_path.exists() and test_data_path.is_dir()):
                #     print(f'{test_data_path} not exists')
                #     return ToolSourceExtractResult_1002(msg="test-data not exists")

                # Resources
                xml_tool_source = XmlToolSource(folder_name=folder_name,
                                                user_space=self.user_space,
                                                user_id=self.user_id)
                # JudgmentResourcesexistence
                parseResult = xml_tool_source.to_dict()
                if parseResult.code != 0:
                    return parseResult

                data = parseResult.data

                # Judgmentexistence xml <executable> Declared executable file
                executable = data.get("executable")
                if executable is not None:
                    exec_path = Path(self.unzip_path, folder_name, executable)
                    if not (exec_path.exists() and exec_path.is_file()):
                        print(f'{exec_path} not exists')
                        # return None
                        return ToolSourceExtractResult_1003(msg=f"executable not exists: {executable}")
                return ToolSourceExtractResult_0(msg="success", data=xml_tool_source)
            else:
                print(f"{path} not exists")
                return ToolSourceExtractResult_1004(msg="zipfile not exists")
        except Exception as e:
            print(f"failed to extract xml_tool_source: {self.zip_name}")
            print(e)
            return ToolSourceExtractResult_1005(msg=f"failed to extract_xml_tool_source: {self.zip_name}")
