from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    APP_ENV: str = Field(default="development", validation_alias="APP_ENV_NOT_USED")


@lru_cache
def get_settings() -> Settings:
    return Settings()
