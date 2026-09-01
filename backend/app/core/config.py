from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "紫微斗數分析系統"
    jwt_secret: str = "change-me-in-railway-variables"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    cors_origins: str = "*"
    default_longitude: float = 114.17     # 香港
    default_tz_offset: float = 8.0
    strict_tables: bool = False           # True 時拒用未覆核的流派表
    llm_polish_enabled: bool = False      # 預設關。開啟也只潤飾文字，不參與推算。

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
