from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, BaseSettings, PostgresDsn, validator


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    DB_HOSTNAME: str = 'db'
    DB_USER: str = 'postgres'
    DB_PASSWORD: str
    DB_PORT: str = '5432'
    DB_DBNAME: str = 'postgres'
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("DB_USER"),
            password=values.get("DB_PASSWORD"),
            host=values.get("DB_HOSTNAME"),
            port=values.get('DB_PORT'),
            path=f"/{values.get('DB_DBNAME') or ''}",
        )

    DEFAULT_PAGE_SIZE: int = 50

    SECRET_KEY: str
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    class Config:
        case_sensitive = True


def get_setting(**kwargs) -> Settings:
    load_dotenv()
    return Settings(**kwargs)
