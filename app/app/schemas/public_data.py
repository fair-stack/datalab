from pydantic import BaseModel
from typing import Optional
class PublicDatasetSchema(BaseModel):
    id: str
    icon: str
    name: str
    access: str
    label: str
    data_type: str
    user: str
    links: str
    files: Optional[int]
    data_size: Optional[int]
    organization_name: Optional[str]
    date_published: Optional[str]
    description: Optional[str]
    # ftp_user: Optional[str]
    # ftp_password: Optional[str]
    # ftp_ip: Optional[str]
    # ftp_port: Optional[str]
    name_zh: Optional[str]
    name_en: Optional[str]




class PublicDataFileSchema(BaseModel):
    id: str
    datasets: str
    name: str
    data_path : str
    data_size: str
    access: str
    deleted : str
    user: str
    is_file: bool
    store_name: str
    description: Optional[str]
    from_source: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    data_type: Optional[str]
    storage_service: Optional[str]
    file_extension: Optional[str]
    alias_name: Optional[str]
    parent: Optional[str]
    deps: int
