from typing import Optional, List, Dict

from pydantic import BaseModel


class Analysis2CreateSchema(BaseModel):
    skeleton: str
    is_trial: bool = False
    name: str
    description: Optional[str]


class Analysis2UpdateSchema(BaseModel):
    name: Optional[str]
    description: Optional[str]
    inputs: Optional[List[Dict]]
    outputs: Optional[List[Dict]]
    state: Optional[str]
