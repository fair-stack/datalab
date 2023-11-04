from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class AnalysisStepElementUpdateSchema(BaseModel):
    data: Optional[Any]
    inputs: Optional[List[Dict[str, Any]]]
    outputs: Optional[List[Dict[str, Any]]]
    is_selected: Optional[bool]
    state: Optional[str]
