from typing import Optional, Dict

from pydantic import BaseModel


class UiCreateForm(BaseModel):
    title: str
    intro: Optional[str]
    styles_start: Optional[Dict]
    styles_stats: Optional[Dict]
    styles_copyright: Optional[Dict]


class UiUpdateForm(BaseModel):
    title: Optional[str]
    intro: Optional[str]
    styles_start: Optional[Dict]
    styles_stats: Optional[Dict]
    styles_copyright: Optional[Dict]
