import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    from app.database import get_db

    async def _override_get_db():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=None)
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def client_db_fail():
    from app.main import app
    from app.database import get_db

    async def _override_get_db_fail():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Connection refused"))
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db_fail
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
