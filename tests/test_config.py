from app.config import Settings, get_settings


def test_settings_app_env_default():
    s = Settings(DATABASE_URL="postgresql+asyncpg://test:test@localhost/testdb")
    assert s.APP_ENV == "development"


def test_settings_accepts_database_url():
    url = "postgresql+asyncpg://user:pass@localhost/mydb"
    s = Settings(DATABASE_URL=url)
    assert s.DATABASE_URL == url


def test_get_settings_returns_singleton():
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    get_settings.cache_clear()
