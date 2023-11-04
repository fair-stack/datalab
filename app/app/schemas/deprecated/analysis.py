from typing import Optional

from pydantic import BaseModel


class AnalysisCreateSchema(BaseModel):
    skeleton: str
    is_trial: bool = False
    name: str
    description: Optional[str]
