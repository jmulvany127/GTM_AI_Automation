import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    DATABASE_URL: str
    APP_ENV: str = "development"
    ANTHROPIC_API_KEY: str
    HUBSPOT_ACCESS_TOKEN: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


USER_FULL_NAME = os.getenv("USER_FULL_NAME", "GTM Agent")
USER_EMAIL = os.getenv("USER_EMAIL", "")

# Domino AI product context
COMPANY_NAME = os.getenv("COMPANY_NAME", "Domino AI")
COMPANY_LOCATION = os.getenv("COMPANY_LOCATION", "New York City, NY")
COMPANY_DESCRIPTION = os.getenv("COMPANY_DESCRIPTION", "")
PRODUCT_DESCRIPTION = os.getenv("PRODUCT_DESCRIPTION", "")
VALUE_PROPOSITION = os.getenv("VALUE_PROPOSITION", "")
TARGET_CUSTOMER = os.getenv("TARGET_CUSTOMER", "")
KEY_INTEGRATIONS = os.getenv("KEY_INTEGRATIONS", "")
KEY_PAIN_POINTS_WE_SOLVE = os.getenv("KEY_PAIN_POINTS_WE_SOLVE", "")
SENDER_TITLE = os.getenv("SENDER_TITLE", "GTM Engineer")
SENDER_COMPANY = os.getenv("SENDER_COMPANY", "Domino AI")
