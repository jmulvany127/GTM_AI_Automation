import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db

_NOW = datetime(2026, 6, 16, 12, 0, 0)

_ANALYSIS_DICT = {
    "company_summary": "A tech company",
    "persona_type": "Champion",
    "pain_points": "Manual processes",
    "buying_signals": "Requested demo",
    "objections": "Budget concerns",
    "fit_score": 75,
    "urgency_score": 60,
    "overall_score": 70,
    "recommended_action": "Schedule call",
    "confidence_score": 0.8,
    "raw_ai_json": '{"fit_score": 75}',
}


def _make_lead(**kwargs):
    defaults = dict(
        id=1, first_name="Jane", last_name="Smith",
        email="jane@example.com", company="Acme Corp",
        job_title="VP Sales", company_website="acme.com",
        source="LinkedIn", notes=None, status="new",
        created_at=_NOW, updated_at=_NOW,
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


@asynccontextmanager
async def _client_with_db(mock_session):
    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_analyze_lead_returns_200_with_correct_structure():
    lead = _make_lead()
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(lead))

    async def _refresh(obj):
        obj.id = 1
        obj.created_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    with patch(
        "app.routers.analysis.ai_service.analyze_lead",
        new=AsyncMock(return_value=_ANALYSIS_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post("/leads/1/analyze")

    assert response.status_code == 200
    data = response.json()
    assert data["lead_id"] == 1
    assert data["fit_score"] == 75
    assert data["urgency_score"] == 60
    assert data["overall_score"] == 70
    assert data["confidence_score"] == 0.8
    assert data["persona_type"] == "Champion"


async def test_analyze_lead_returns_404_for_missing_lead():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(None))

    async with _client_with_db(mock) as client:
        response = await client.post("/leads/999/analyze")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"
