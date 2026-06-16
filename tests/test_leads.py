import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db

_NOW = datetime(2024, 1, 1, 12, 0, 0)


def _make_lead(**kwargs):
    defaults = dict(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        company=None,
        job_title=None,
        company_website=None,
        source=None,
        notes=None,
        status="new",
        created_at=_NOW,
        updated_at=_NOW,
    )
    defaults.update(kwargs)
    lead = MagicMock()
    for k, v in defaults.items():
        setattr(lead, k, v)
    return lead


def _scalar_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _scalars_all_result(objs):
    r = MagicMock()
    r.scalars.return_value.all.return_value = objs
    return r


@asynccontextmanager
async def _client_with_db(mock_session):
    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_create_lead_returns_201():
    mock = AsyncMock()

    async def _refresh(obj):
        obj.id = 1
        obj.created_at = _NOW
        obj.updated_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    async with _client_with_db(mock) as client:
        response = await client.post(
            "/leads",
            json={"first_name": "John", "last_name": "Doe", "email": "john@example.com"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "john@example.com"
    assert data["status"] == "new"
    assert data["first_name"] == "John"
