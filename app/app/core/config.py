import os
import secrets
from typing import List, Optional, Union
import pathlib
from dotenv import load_dotenv
from pydantic import BaseSettings, validator
from enum import Enum
# load .env file
load_dotenv()


class Settings(BaseSettings):
    API_STR: str = "/api"

    SECRET_KEY: str = secrets.token_urlsafe(32)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    EMAIL_VERIFY_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    RESET_PASSWORD_TOKEN_EXPIRE_MINUTES: int = 60
    RESET_PASSWORD_EMAIL_SENT_FREQUENCY_SECONDS: int = 30

    # SERVER_NAME: str
    SERVER_HOST: str = '127.0.0.1'
    MARKET_USER: str = "admin@datalab.casdc.cn"
    VERSION: str = "v1.1.1"
    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ['*']
    BACKEND_CORS_ORIGINS: List[str] = ['*']

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "DataLab"

    SMTP_TLS: Optional[bool] = False
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    #
    # EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    # EMAIL_TEMPLATES_DIR: str = "/app/app/email-templates/build"
    # EMAILS_ENABLED: bool = False
    #
    # @validator("EMAILS_ENABLED", pre=True)
    # def get_emails_enabled(cls, v: bool, values: Dict[str, Any]) -> bool:
    #     return bool(
    #         values.get("SMTP_HOST")
    #         and values.get("SMTP_PORT")
    #         and values.get("EMAILS_FROM_EMAIL")
    #     )
    #
    # EMAIL_TEST_USER: EmailStr = "test@example.com"  # type: ignore
    # FIRST_SUPERUSER: EmailStr
    # FIRST_SUPERUSER_PASSWORD: str
    # USERS_OPEN_REGISTRATION: bool = False

    MONGODB_USER: Optional[str]
    MONGODB_PASSWORD: Optional[str]
    MONGODB_SERVER: str
    MONGODB_PORT: int = 27017
    MONGODB_DB: str
    MONGODB_AUTH_SOURCE: Optional[str]

    DOCKER_TCP: Optional[str]
    DOCKER_TIMEOUT: int = 10
    DOCKER_VERSION: str = "auto"

    # app/[api, core, db,..] in app
    # BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BASE_DIR: str = "/home/data_storage"

    # tools
    TOOL_PATH: str = "storage_tools"
    TOOL_ZIP_PATH: str = "storage_tools_zips"

    # storage_data
    DATA_PATH: str = "storage_data"
    DATA_TEMP_PATH: str = "storage_data_temp"

    # configs
    CONFIGS_PATH: str = "storage_configs"

    # Skeletons
    SKELETON_PATH: str = "storage_skeletons"

    # Function Service
    FaaS_GATEWAY: str
    FaaS_USER: str
    FaaS_PASSWORD: str
    ASYNC_FUNCTION_DOMAIN: str
    FUNCTION_DOMAIN: str
    BUILD_DIR: str
    TEMPLATE_DIR: str
    STANDALONE_FUNCTION_DOMAIN: str
    # Minio
    MINIO_URL: str
    MINIO__ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    VER_DATA_DB: int = 2
    TASK_PUBLISHER_DB: int = 5
    PLANT_CONFIG_DB: int = 6
    FILE_CACHE_DB: int = 9
    USED_STORAGE_CUMULATIVE_DB: int = 11
    SKELETON_DATA_CACHE_DB: int = 12
    AUTH_CACHE_DB: int = 13

    # components audit field allow
    AUDIT_ALLOW: set = {"Approved by review", "Pending review", "Failed to pass the audit"}
    FLOW_EVENT_TYPES: set = {"Submitted", "Commit failure", "Startup", "Startup", "Operator execution", "Operator execution", "Operator execution",
                             "Step execution", "Step execution", "Step execution", "The tool executed successfully."}
    COMPUTING_START: str = "Start"
    COMPUTING_PENDING: str = "Pending"
    COMPUTING_FAILED: str = "Failed"
    COMPUTING_SUCCESS: str = "Success"
    KUBERNETES_CONFIG = os.path.join(pathlib.Path(__file__).parent.parent.__fspath__(), 'utils/k8s_util/config')
    HARBOR_URL: str
    HARBOR_PROJECTS: str
    HARBOR_ROBOT_NAME: str
    HARBOR_USER: str
    HARBOR_PASSWORD: str
    MARKET_API: str
    MARKET_COMPONENT_DOWNLOAD_DIR: str = os.path.join(pathlib.Path(__file__).parent.parent.__fspath__(), 'market_components')
    MARKET_FRONT_COMPONENT_DOWNLOAD_DIR: str = "/home/datalab/dist/market_component"
    MARKET_FRONT_COMPONENT_DOWNLOAD_CACHE_DIR: str = "/home/datalab/dist/market_component_cache"
    # MARKET_FRONT_COMPONENT_DOWNLOAD_DIR: str = "./dist/market_component"
    # MARKET_FRONT_COMPONENT_DOWNLOAD_CACHE_DIR: str = "./dist/market_component_cache"
    NOTEBOOK_GATEWAY_ADMIN: str
    NOTEBOOK_GATEWAY_ADMIN_UPSTREAM: str
    NOTEBOOK_GATEWAY_ADMIN_ROUTER: str
    NOTEBOOK_GATEWAY_URI: str
    BACKEND_COMPONENT: str = "back-end"
    FRONTEND_COMPONENT: str = "front-end"
    COMPONENT_TYPE: list = [BACKEND_COMPONENT, FRONTEND_COMPONENT]
    LAKE_ADMIN_URL: str
    LAKE_ADMIN_USERNAME: str
    LAKE_ADMIN_TOKEN: str
    STANDALONE_MODEL: bool

    class ComputeEvent(Enum):
        task = "TASK"
        experiment = "EXPERIMENT"
        analysis = "ANALYSIS"

    class Config:
        case_sensitive = True
        # Set to be identified .env Files and Encoding
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
