from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import UploadFile

from pydantic import BaseModel


class IndexUiSchema(BaseModel):
    id: str
    title: Optional[str]
    intro: Optional[str]
    background: Optional[str]
    styles_start: Optional[Dict]
    styles_stats: Optional[Dict]
    styles_copyright: Optional[Dict]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
