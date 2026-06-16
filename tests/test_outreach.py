import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db

_NOW = datetime(2026, 6, 16, 14, 0, 0)

_OUTREACH_DICT = {
    "subject": "Automate your pipeline, Jane",
    "email_body": "Hi Jane, we help VP Sales leaders at companies like Acme Corp eliminate manual processes. Worth a quick call?",
    "follow_up_email": "Hi Jane, just following up. Would 20 minutes this week work to explore if we can help?",
    "linkedin_message": "Hi Jane, saw you're scaling sales at Acme Corp — we help reduce manual work. Worth connecting?",
    "call_notes": "Ask about CRM setup. Explore pain around manual reporting. Understand team size.",
}


def _make_lead(**kwargs):
    defaults = dict(
        id=1, first_name="Jane", last_name="Smith",
        email="jane@example.com", company="Acme Corp",
        job_title="VP Sales", company_website="acme.com",
        source="LinkedIn", notes=None, status="analyzed",
        created_at=_NOW, updated_at=_NOW,
    )
    defaults.update(kwargs)
    lead = MagicMock()
    for k, v in defaults.items():
        setattr(lead, k, v)
    return lead


def _make_analysis(**kwargs):
    defaults = dict(
        id=1, lead_id=1,
        persona_type="Champion",
        pain_points="Manual sales processes",
        buying_signals="Requested a demo",
        recommended_action="Schedule discovery call",
        overall_score=75,
        created_at=_NOW,
    )
    defaults.update(kwargs)
    analysis = MagicMock()
    for k, v in defaults.items():
        setattr(analysis, k, v)
    return analysis


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


async def test_generate_outreach_returns_200_with_correct_structure():
    lead = _make_lead()
    analysis = _make_analysis()
    mock = AsyncMock()
    mock.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
    ])

    async def _refresh(obj):
        obj.id = 1
        obj.created_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    with patch(
        "app.routers.outreach.outreach_service.generate_outreach",
        new=AsyncMock(return_value=_OUTREACH_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post("/leads/1/generate-outreach")

    assert response.status_code == 200
    data = response.json()
    assert data["lead_id"] == 1
    assert isinstance(data["subject"], str)
    assert isinstance(data["email_body"], str)
    assert isinstance(data["linkedin_message"], str)


async def test_generate_outreach_returns_404_for_missing_lead():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=_scalar_result(None))

    async with _client_with_db(mock) as client:
        response = await client.post("/leads/999/generate-outreach")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


async def test_generate_outreach_returns_404_when_no_analysis_exists():
    lead = _make_lead()
    mock = AsyncMock()
    mock.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
    ])

    async with _client_with_db(mock) as client:
        response = await client.post("/leads/1/generate-outreach")

    assert response.status_code == 404
    assert "analyze" in response.json()["detail"].lower()


async def test_generate_outreach_email_body_is_string_on_success():
    lead = _make_lead()
    analysis = _make_analysis()
    mock = AsyncMock()
    mock.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
    ])

    async def _refresh(obj):
        obj.id = 2
        obj.created_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    with patch(
        "app.routers.outreach.outreach_service.generate_outreach",
        new=AsyncMock(return_value=_OUTREACH_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post("/leads/1/generate-outreach")

    assert response.status_code == 200
    assert isinstance(response.json()["email_body"], str)


async def test_generate_outreach_linkedin_message_is_string_on_success():
    lead = _make_lead()
    analysis = _make_analysis()
    mock = AsyncMock()
    mock.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
    ])

    async def _refresh(obj):
        obj.id = 3
        obj.created_at = _NOW

    mock.refresh = AsyncMock(side_effect=_refresh)

    with patch(
        "app.routers.outreach.outreach_service.generate_outreach",
        new=AsyncMock(return_value=_OUTREACH_DICT),
    ):
        async with _client_with_db(mock) as client:
            response = await client.post("/leads/1/generate-outreach")

    assert response.status_code == 200
    assert isinstance(response.json()["linkedin_message"], str)
