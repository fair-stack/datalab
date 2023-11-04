from collections import namedtuple


APIResult = namedtuple("APIResult", ["code", "msg", "total", "data"])


# ToolSource relevant
# code: 1001 ->
ToolSourceExtractResult = namedtuple("ToolSourceExtractResult", ["code", "msg", "data"])
ToolSourceExtractResult_0 = namedtuple("ToolSourceExtractResult_0", ["code", "msg", "data"], defaults=[0, "success", None])
ToolSourceExtractResult_1001 = namedtuple("ToolSourceExtractResult_1001", ["code", "msg", "data"], defaults=[1001, "xml not exists: {xml_name}", None])
ToolSourceExtractResult_1002 = namedtuple("ToolSourceExtractResult_1002", ["code", "msg", "data"], defaults=[1002, "test-data not exists", None])
ToolSourceExtractResult_1003 = namedtuple("ToolSourceExtractResult_1003", ["code", "msg", "data"], defaults=[1003, "executable not exists: {executable}", None])
ToolSourceExtractResult_1004 = namedtuple("ToolSourceExtractResult_1004", ["code", "msg", "data"], defaults=[1004, "zipfile not exists", None])
ToolSourceExtractResult_1005 = namedtuple("ToolSourceExtractResult_1005", ["code", "msg", "data"], defaults=[1005, "failed to extract_xml_tool_source: {zip_name}", None])

# code: 2001
ToolSourceParseResult = namedtuple("ToolSourceParseResult", ["code", "msg", "data"])
ToolSourceParseResult_0 = namedtuple("ToolSourceParseResult_0", ["code", "msg", "data"], defaults=[0, "success", None])
ToolSourceParseResult_2001 = namedtuple("ToolSourceParseResult_2001", ["code", "msg", "data"], defaults=[2001, "ToolSourceParseResult is None", None])
ToolSourceParseResult_2002 = namedtuple("ToolSourceParseResult_2002", ["code", "msg", "data"], defaults=[2002, "invalid xml, `req_field is missing: {req_field}", None])
ToolSourceParseResult_2003 = namedtuple("ToolSourceParseResult_2003", ["code", "msg", "data"], defaults=[2003, "invalid requirement.type: {_type}", None])
ToolSourceParseResult_2004 = namedtuple("ToolSourceParseResult_2004", ["code", "msg", "data"], defaults=[2004, "invalid xml, inputs.param.req_field is missing: {req_field}", None])
ToolSourceParseResult_2005 = namedtuple("ToolSourceParseResult_2005", ["code", "msg", "data"], defaults=[2005, "invalid outputs.data.type: {outputdata_type}", None])
ToolSourceParseResult_2006 = namedtuple("ToolSourceParseResult_2006", ["code", "msg", "data"], defaults=[2006, "options are missing for inputs.param.type {param_type}", None])
ToolSourceParseResult_2007 = namedtuple("ToolSourceParseResult_2007", ["code", "msg", "data"], defaults=[2007, "invalid inputs.param.option.type: {option_type}", None])
ToolSourceParseResult_2008 = namedtuple("ToolSourceParseResult_2008", ["code", "msg", "data"], defaults=[2008, "invalid xml, outputs.data.req_field is missing: {req_field}", None])
ToolSourceParseResult_2009 = namedtuple("ToolSourceParseResult_2009", ["code", "msg", "data"], defaults=[2009, "failed to save xml to db: {xml_name}", None])

# Skeleton relevant
