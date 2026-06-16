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


async def test_list_leads_returns_200():
    lead1 = _make_lead(id=1, email="a@example.com")
    lead2 = _make_lead(id=2, email="b@example.com")
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalars_all_result([lead1, lead2]))

    async with _client_with_db(mock) as client:
        response = await client.get("/leads")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["email"] == "a@example.com"
    assert data[1]["email"] == "b@example.com"


async def test_get_lead_returns_correct_lead():
    lead = _make_lead(id=42, email="target@example.com")
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(lead))

    async with _client_with_db(mock) as client:
        response = await client.get("/leads/42")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["email"] == "target@example.com"


async def test_get_lead_returns_404_for_missing():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(None))

    async with _client_with_db(mock) as client:
        response = await client.get("/leads/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


async def test_patch_lead_updates_fields():
    lead = _make_lead(id=1, company="Old Corp")
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(lead))

    async with _client_with_db(mock) as client:
        response = await client.patch("/leads/1", json={"company": "New Corp"})

    assert response.status_code == 200
    assert response.json()["company"] == "New Corp"


async def test_patch_lead_returns_404_for_missing():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(None))

    async with _client_with_db(mock) as client:
        response = await client.patch("/leads/999", json={"company": "X"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


async def test_delete_lead_returns_204():
    lead = _make_lead(id=1)
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(lead))

    async with _client_with_db(mock) as client:
        response = await client.delete("/leads/1")

    assert response.status_code == 204
    mock.delete.assert_called_once_with(lead)
    mock.commit.assert_called_once()


async def test_delete_lead_returns_404_for_missing():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(None))

    async with _client_with_db(mock) as client:
        response = await client.delete("/leads/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


async def test_delete_lead_returns_409_on_integrity_error():
    lead = _make_lead(id=1)
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(lead))
    mock.commit = AsyncMock(
        side_effect=IntegrityError("FK violation", {}, Exception("foreign key constraint"))
    )

    async with _client_with_db(mock) as client:
        response = await client.delete("/leads/1")

    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot delete lead with associated records"


async def test_create_lead_duplicate_email_returns_409():
    mock = AsyncMock()
    mock.commit = AsyncMock(
        side_effect=IntegrityError("INSERT", {}, Exception("unique constraint violation"))
    )

    async with _client_with_db(mock) as client:
        response = await client.post(
            "/leads",
            json={"first_name": "Jane", "last_name": "Doe", "email": "duplicate@example.com"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


async def test_patch_lead_duplicate_email_returns_409():
    lead = _make_lead(id=1)
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(lead))
    mock.commit = AsyncMock(
        side_effect=IntegrityError("UPDATE", {}, Exception("unique constraint violation"))
    )

    async with _client_with_db(mock) as client:
        response = await client.patch("/leads/1", json={"email": "taken@example.com"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"
