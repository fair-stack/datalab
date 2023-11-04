from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import UploadFile

from pydantic import BaseModel


class PlatformSchema(BaseModel):
    id: str
    name: str
    logo: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

