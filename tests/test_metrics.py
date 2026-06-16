import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db


@asynccontextmanager
async def _client_with_db(mock_session):
    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


async def test_roi_endpoint_returns_200_with_correct_structure():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(5),    # total_leads_processed
        _scalar_result(3),    # high_priority_leads
        _scalar_result(125.0),  # sum of estimated_time_saved_minutes
        _scalar_result(30.5),   # average automated_time_seconds
        _scalar_result(72.4),   # average overall_score
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.get("/metrics/roi")

    assert response.status_code == 200
    data = response.json()
    expected_keys = {
        "total_leads_processed",
        "high_priority_leads",
        "estimated_hours_saved",
        "average_processing_time_seconds",
        "average_lead_score",
        "hubspot_sync_success_rate",
    }
    assert expected_keys == set(data.keys())


async def test_roi_endpoint_returns_safe_defaults_when_no_data():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(None),
        _scalar_result(None),
        _scalar_result(None),
        _scalar_result(None),
        _scalar_result(None),
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.get("/metrics/roi")

    assert response.status_code == 200
    data = response.json()
    assert data["total_leads_processed"] == 0
    assert data["high_priority_leads"] == 0
    assert data["estimated_hours_saved"] == 0.0
    assert data["average_processing_time_seconds"] == 0.0
    assert data["average_lead_score"] == 0.0
    assert data["hubspot_sync_success_rate"] == 0.0


async def test_total_leads_processed_is_integer():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(7),
        _scalar_result(2),
        _scalar_result(60.0),
        _scalar_result(15.0),
        _scalar_result(68.0),
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.get("/metrics/roi")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["total_leads_processed"], int)


async def test_estimated_hours_saved_is_float():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(2),
        _scalar_result(1),
        _scalar_result(90.0),   # 90 minutes = 1.5 hours
        _scalar_result(20.0),
        _scalar_result(80.0),
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.get("/metrics/roi")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["estimated_hours_saved"], float)
    assert data["estimated_hours_saved"] == 1.5


async def test_hubspot_sync_success_rate_returns_zero():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(1),
        _scalar_result(1),
        _scalar_result(30.0),
        _scalar_result(10.0),
        _scalar_result(90.0),
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.get("/metrics/roi")

    assert response.status_code == 200
    data = response.json()
    assert data["hubspot_sync_success_rate"] == 0.0
