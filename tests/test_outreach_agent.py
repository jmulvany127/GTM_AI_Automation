import json
import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db

_NOW = datetime(2026, 6, 16, 14, 0, 0)

_AGENT_RESULT = {
    "chosen_channel": "email",
    "agent_reasoning": "Email is best.",
    "requires_human_review": False,
    "review_reason": None,
    "personalisation_notes": None,
}

_ANALYSIS_DICT = {
    "company_summary": "Tech company",
    "persona_type": "Champion",
    "pain_points": "Manual processes",
    "buying_signals": "Demo requested",
    "objections": None,
    "fit_score": 80,
    "urgency_score": 70,
    "overall_score": 78,
    "recommended_action": "Schedule call",
    "confidence_score": 0.85,
    "raw_ai_json": None,
}

_OUTREACH_DICT = {
    "subject": "Automate your pipeline",
    "email_body": "Hi Jane, we can help automate your sales process.",
    "follow_up_email": "Following up on my last message.",
    "linkedin_message": "Hi Jane, saw you are scaling sales at Acme Corp.",
    "call_notes": "Ask about CRM setup.",
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


def _make_analysis(**kwargs):
    defaults = dict(
        id=1, lead_id=1, persona_type="Champion",
        pain_points="Manual processes", buying_signals="Demo requested",
        overall_score=78, confidence_score=0.85,
        recommended_action="Schedule call",
        created_at=_NOW,
    )
    defaults.update(kwargs)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_outreach(**kwargs):
    defaults = dict(
        id=1, lead_id=1,
        subject="Automate your pipeline",
        email_body="Hi Jane, we can help automate your sales process.",
        follow_up_email="Following up on my last message.",
        linkedin_message="Hi Jane, saw you are scaling sales at Acme Corp.",
        call_notes="Ask about CRM setup.",
        created_at=_NOW,
    )
    defaults.update(kwargs)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _scalar_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _agent_response(plan_dict: dict):
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps(plan_dict)
    return mock_response


@asynccontextmanager
async def _client_with_db(mock_session):
    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 1: POST /leads/{id}/run-outreach-agent returns 200 with correct shape
# ---------------------------------------------------------------------------

async def test_run_outreach_agent_returns_200_with_correct_shape():
    lead = _make_lead()
    analysis = _make_analysis()
    outreach = _make_outreach()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(outreach),
    ])
    mock_db.refresh = AsyncMock()

    with patch("app.routers.leads.run_outreach_agent", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = _AGENT_RESULT

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["lead_id"] == 1
    assert "chosen_channel" in data
    assert "agent_reasoning" in data
    assert "requires_human_review" in data
    assert "review_reason" in data
    assert "execution_status" in data
    assert "created_at" in data
    assert data["chosen_channel"] == "email"
    assert data["agent_reasoning"] == "Email is best."
    assert data["requires_human_review"] is False


# ---------------------------------------------------------------------------
# Test 2: POST /leads/{id}/run-outreach-agent returns 404 when outreach missing
# ---------------------------------------------------------------------------

async def test_run_outreach_agent_returns_404_when_outreach_missing():
    lead = _make_lead()
    analysis = _make_analysis()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),  # no outreach
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 404
    assert "outreach" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 3: Service fallback on exception
# ---------------------------------------------------------------------------

async def test_service_fallback_on_exception():
    from app.services.outreach_agent_service import run_outreach_agent

    lead_dict = {
        "id": 1, "first_name": "Jane", "last_name": "Smith",
        "email": "jane@example.com", "company": "Acme Corp",
        "job_title": "VP Sales", "source": "LinkedIn",
        "status": "new", "company_website": "acme.com",
    }
    analysis_dict = {
        "id": 1, "persona_type": "Champion",
        "pain_points": "Manual processes", "buying_signals": "Demo requested",
        "overall_score": 78, "confidence_score": 0.85,
        "recommended_action": "Schedule call",
    }
    outreach_dict = {
        "id": 1, "subject": "Automate your pipeline",
        "email_body": "Hi Jane.",
        "linkedin_message": "Hi Jane on LinkedIn.",
        "follow_up_email": "Following up.",
    }

    with patch("app.services.outreach_agent_service.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=Exception("API failure"))

        result = await run_outreach_agent(lead_dict, analysis_dict, outreach_dict)

    assert result["fallback"] is True
    assert result["chosen_channel"] == "email"
    assert result["requires_human_review"] is True


# ---------------------------------------------------------------------------
# Test 4: Handoff called when orchestrator executes generate_outreach
# ---------------------------------------------------------------------------

async def test_handoff_called_when_generate_outreach_executed():
    lead = _make_lead()
    analysis = _make_analysis()
    outreach = _make_outreach()

    mock_db = AsyncMock()
    # DB call sequence for /run-agent with ["analyze_lead", "generate_outreach"]:
    #   1. Fetch lead (run_agent_endpoint)
    #   2. Fetch latest_analysis for planning (run_agent_endpoint)
    #   3. Fetch analysis inside execute_generate_outreach
    #   4. Fetch analysis for outreach agent handoff (after generate_outreach)
    #   5. Fetch outreach for outreach agent handoff
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),       # 1. fetch lead
        _scalar_result(None),       # 2. latest_analysis for plan (None is fine — plan comes from agent mock)
        _scalar_result(analysis),   # 3. analysis inside execute_generate_outreach
        _scalar_result(analysis),   # 4. analysis for handoff
        _scalar_result(outreach),   # 5. outreach for handoff
    ])

    plan = {
        "actions": ["analyze_lead", "generate_outreach"],
        "requires_human_review": False,
        "reasoning_summary": "Analyze then generate",
    }

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_gtm_cls, \
         patch("app.routers.workflow.ai_service.analyze_lead", new_callable=AsyncMock) as mock_analyze, \
         patch("app.routers.workflow.outreach_service.generate_outreach", new_callable=AsyncMock) as mock_generate, \
         patch("app.routers.workflow.run_outreach_agent", new_callable=AsyncMock) as mock_outreach_agent:

        mock_gtm_client = AsyncMock()
        mock_gtm_cls.return_value = mock_gtm_client
        mock_gtm_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        mock_analyze.return_value = _ANALYSIS_DICT
        mock_generate.return_value = _OUTREACH_DICT
        mock_outreach_agent.return_value = _AGENT_RESULT

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-agent")

    assert response.status_code == 200
    mock_outreach_agent.assert_called_once()
