from pydantic import BaseModel
from typing import Optional, Any


class FairMarketComponentSchema(BaseModel):
    id: str
    bundle: str
    CreateAt: str
    UpdateAt: str
    name: str
    logo: str
    description: Optional[str] = None
    category : str
    size: int
    authorName: str
    softwareName: Optional[str] = None
    softwareLogo: Optional[str] = None
    publishStatus: Optional[int] = None
    enable: bool
    installed: str
    installed_at: Optional[str] = None
    installed_user: Optional[str] = None
    componentType: str
    parameters: Optional[Any] = None


class FairMarketComponentsTreeSchema(BaseModel):
    # id: str
    category: str
    counts: int


class MarketComponentsInstallTaskSchema(BaseModel):
    id: str
    source: str
    installed_user: str
    installed_at: str
    reinstall: bool
    reinstall_nums: int
    status: str
    source_type: str
