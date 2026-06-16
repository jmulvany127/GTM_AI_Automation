from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    DATABASE_URL: str
    APP_ENV: str = "development"
    ANTHROPIC_API_KEY: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
