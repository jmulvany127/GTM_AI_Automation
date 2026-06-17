import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("HUBSPOT_ACCESS_TOKEN", "test-hubspot-token")

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db

_NOW = datetime(2026, 6, 17, 12, 0, 0)

_ANALYSIS_DICT = {
    "pain_points": "High customer churn",
    "objections": "Price is too high",
    "competitors": "Competitor X",
    "budget_signals": "Looking to spend Q4",
    "decision_timeline": "Next quarter",
    "buying_intent_score": 7.5,
    "recommended_follow_up": "Schedule a demo",
    "crm_note": "Strong interest, follow up this week",
    "follow_up_email": "Hi there, following up on our call...",
}

_LONG_TRANSCRIPT = (
    "This is a long transcript that exceeds fifty characters and contains "
    "meaningful sales conversation content about the product."
)


def _scalar_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _make_lead(**kwargs):
    defaults = dict(id=1, first_name="Jane", last_name="Smith", email="jane@acme.com")
    defaults.update(kwargs)
    lead = MagicMock()
    for k, v in defaults.items():
        setattr(lead, k, v)
    return lead


@asynccontextmanager
async def _client_with_db(mock_session):
    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_analyze_no_lead_id_returns_200_with_all_fields():
    mock = AsyncMock()

    async def _refresh(obj):
        obj.id = 1
        obj.created_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    with patch(
        "app.routers.call_notes.call_intelligence_service.analyze_transcript",
        new=AsyncMock(return_value=_ANALYSIS_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post(
                "/call-notes/analyze",
                json={"transcript": _LONG_TRANSCRIPT},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["lead_id"] is None
    assert data["pain_points"] == "High customer churn"
    assert data["objections"] == "Price is too high"
    assert data["competitors"] == "Competitor X"
    assert data["budget_signals"] == "Looking to spend Q4"
    assert data["decision_timeline"] == "Next quarter"
    assert data["buying_intent_score"] == 7.5
    assert data["recommended_follow_up"] == "Schedule a demo"
    assert data["crm_note"] == "Strong interest, follow up this week"
    assert data["follow_up_email"] == "Hi there, following up on our call..."
    assert "created_at" in data


async def test_analyze_valid_lead_id_returns_200_and_links_lead():
    lead = _make_lead(id=42)
    mock = AsyncMock()
    # First execute: lead lookup; second execute: crm_log lookup (no match)
    mock.execute = AsyncMock(side_effect=[_scalar_result(lead), _scalar_result(None)])

    async def _refresh(obj):
        obj.id = 5
        obj.created_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    with patch(
        "app.routers.call_notes.call_intelligence_service.analyze_transcript",
        new=AsyncMock(return_value=_ANALYSIS_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post(
                "/call-notes/analyze",
                json={"lead_id": 42, "transcript": _LONG_TRANSCRIPT},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["lead_id"] == 42


async def test_analyze_invalid_lead_id_returns_404():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(None))

    with patch(
        "app.routers.call_notes.call_intelligence_service.analyze_transcript",
        new=AsyncMock(return_value=_ANALYSIS_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post(
                "/call-notes/analyze",
                json={"lead_id": 999, "transcript": _LONG_TRANSCRIPT},
            )

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


async def test_short_transcript_returns_422():
    mock = AsyncMock()
    async with _client_with_db(mock) as client:
        response = await client.post(
            "/call-notes/analyze",
            json={"transcript": "Too short"},
        )
    assert response.status_code == 422


async def test_service_fallback_on_anthropic_exception():
    from app.services.call_intelligence_service import analyze_transcript

    with patch("app.services.call_intelligence_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(side_effect=Exception("API down"))

        result = await analyze_transcript(_LONG_TRANSCRIPT)

    assert result.get("fallback") is True
    assert result["pain_points"] is None
    assert result["buying_intent_score"] is None
    assert instance.messages.create.call_count == 2
