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

# All 10 keys returned by the unified outreach agent
_AGENT_RESULT = {
    "subject": "Automate your pipeline",
    "email_body": "Hi Jane, we can help automate your sales process.",
    "follow_up_email": "Following up on my last message.",
    "linkedin_message": "Hi Jane, saw you are scaling sales at Acme Corp.",
    "call_notes": "Ask about CRM setup.",
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


def _make_log(**kwargs):
    defaults = dict(
        id=1, lead_id=1, outreach_message_id=1,
        chosen_channel="email",
        agent_reasoning="Email is best.",
        requires_human_review=False,
        review_reason=None,
        execution_status="sent",
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
    log = _make_log()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),       # 1. fetch lead
        _scalar_result(None),       # 2. check for existing execution_log (None = no duplicate)
        _scalar_result(analysis),   # 3. fetch analysis (inside leads.py endpoint)
        _scalar_result(analysis),   # 4. fetch analysis inside execute_run_outreach_agent (workflow.py)
        _scalar_result(log),        # 5. fetch log after commit (to build response)
    ])
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()

    with patch("app.routers.workflow.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.workflow.gmail_service.send_email") as mock_gmail, \
         patch("app.routers.workflow.slack_service.send_alert", new_callable=AsyncMock) as mock_slack:

        mock_agent.return_value = {**_AGENT_RESULT}
        mock_gmail.return_value = True
        mock_slack.return_value = None

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
# Test 2: POST /leads/{id}/run-outreach-agent returns 404 when no analysis found
# ---------------------------------------------------------------------------

async def test_run_outreach_agent_returns_404_when_analysis_missing():
    lead = _make_lead()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),   # 1. fetch lead
        _scalar_result(None),   # 2. check for existing execution_log (None = no duplicate)
        _scalar_result(None),   # 3. fetch analysis → not found
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 404
    assert "analysis" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 3: Service fallback returns all content + decision keys with requires_human_review=True
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

    with patch("app.services.outreach_agent_service.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=Exception("API failure"))

        result = await run_outreach_agent(lead_dict, analysis_dict)

    # All 10 keys must be present
    assert result["fallback"] is True
    assert "subject" in result
    assert "email_body" in result
    assert "follow_up_email" in result
    assert "linkedin_message" in result
    assert "call_notes" in result
    assert "chosen_channel" in result
    assert "agent_reasoning" in result
    assert "requires_human_review" in result
    assert "review_reason" in result
    assert "personalisation_notes" in result
    assert result["requires_human_review"] is True
    assert result["chosen_channel"] == "deferred"


# ---------------------------------------------------------------------------
# Test 4: Gmail is called when channel is email and requires_human_review is False
# ---------------------------------------------------------------------------

async def test_gmail_called_when_channel_is_email_and_no_review():
    from app.routers.workflow import execute_run_outreach_agent

    analysis_obj = _make_analysis(overall_score=60)
    lead_obj = _make_lead()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(analysis_obj))
    mock_db.flush = AsyncMock()
    mock_db.add = MagicMock()

    agent_result = {
        **_AGENT_RESULT,
        "chosen_channel": "email",
        "requires_human_review": False,
    }

    with patch("app.routers.workflow.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.workflow.gmail_service.send_email") as mock_gmail, \
         patch("app.routers.workflow.slack_service.send_alert", new_callable=AsyncMock) as mock_slack:

        mock_agent.return_value = agent_result
        mock_gmail.return_value = True
        mock_slack.return_value = None

        result = await execute_run_outreach_agent(lead_obj, mock_db)

    mock_gmail.assert_called_once()


# ---------------------------------------------------------------------------
# Test 5: Gmail is not called when requires_human_review is True
# ---------------------------------------------------------------------------

async def test_gmail_not_called_when_requires_human_review():
    from app.routers.workflow import execute_run_outreach_agent

    analysis_obj = _make_analysis(overall_score=78)
    lead_obj = _make_lead()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(analysis_obj))
    mock_db.flush = AsyncMock()
    mock_db.add = MagicMock()

    agent_result = {
        **_AGENT_RESULT,
        "chosen_channel": "email",
        "requires_human_review": True,
        "review_reason": "Flagged for manual review",
    }

    with patch("app.routers.workflow.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.workflow.gmail_service.send_email") as mock_gmail, \
         patch("app.routers.workflow.slack_service.send_alert", new_callable=AsyncMock) as mock_slack:

        mock_agent.return_value = agent_result
        mock_gmail.return_value = True
        mock_slack.return_value = None

        result = await execute_run_outreach_agent(lead_obj, mock_db)

    mock_gmail.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: Slack lead alert is called when overall_score >= 70 and not requires_human_review
# ---------------------------------------------------------------------------

async def test_slack_alert_called_when_high_score_and_no_review():
    from app.routers.workflow import execute_run_outreach_agent

    analysis_obj = _make_analysis(overall_score=80)
    lead_obj = _make_lead()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(analysis_obj))
    mock_db.flush = AsyncMock()
    mock_db.add = MagicMock()

    agent_result = {
        **_AGENT_RESULT,
        "chosen_channel": "email",
        "requires_human_review": False,
    }

    with patch("app.routers.workflow.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.workflow.gmail_service.send_email") as mock_gmail, \
         patch("app.routers.workflow.slack_service.send_alert", new_callable=AsyncMock) as mock_slack, \
         patch("app.routers.workflow.slack_service.build_lead_alert") as mock_build_alert:

        mock_agent.return_value = agent_result
        mock_gmail.return_value = True
        mock_slack.return_value = None
        mock_build_alert.return_value = {"text": "New lead alert"}

        result = await execute_run_outreach_agent(lead_obj, mock_db)

    mock_slack.assert_called_once()


# ---------------------------------------------------------------------------
# Test 7: Orchestrator dispatches run_outreach_agent as a proper declared action
# ---------------------------------------------------------------------------

async def test_orchestrator_dispatches_run_outreach_agent():
    lead = _make_lead()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),    # 1. fetch lead
        _scalar_result(None),    # 2. check existing metrics (None = not yet run)
        _scalar_result(None),    # 3. fetch latest_analysis for orchestrator planning
    ])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    plan = {
        "actions": ["run_outreach_agent"],
        "requires_human_review": False,
        "reasoning_summary": "Lead is ready for outreach",
    }

    outreach_agent_result = {
        **_AGENT_RESULT,
        "chosen_channel": "email",
        "requires_human_review": False,
    }

    mock_executor = AsyncMock(return_value=outreach_agent_result)

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_gtm_cls, \
         patch.dict("app.routers.workflow._DISPATCH", {"run_outreach_agent": mock_executor}):

        mock_gtm_client = AsyncMock()
        mock_gtm_cls.return_value = mock_gtm_client
        mock_gtm_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-agent")

    assert response.status_code == 200
    data = response.json()
    assert "run_outreach_agent" in data["actions_executed"]


# ---------------------------------------------------------------------------
# Test 8: Deterministic override — personal email domain forces deferred + review
# ---------------------------------------------------------------------------

async def test_deterministic_override_personal_email_forces_deferred():
    from app.services.outreach_agent_service import run_outreach_agent

    llm_response = {
        "subject": "Hello",
        "email_body": "Body text.",
        "follow_up_email": "Follow up.",
        "linkedin_message": "LinkedIn text.",
        "call_notes": None,
        "chosen_channel": "both",
        "requires_human_review": False,
        "review_reason": None,
        "agent_reasoning": "test",
        "personalisation_notes": None,
    }

    lead_dict = {
        "id": 1, "first_name": "Test", "last_name": "User",
        "email": "test@gmail.com", "company": "Some Corp",
        "job_title": "Manager", "source": "Web",
    }
    analysis_dict = {
        "overall_score": 80,
        "confidence_score": 0.9,
        "persona_type": "Champion",
    }

    with patch("app.services.outreach_agent_service.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(llm_response)
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await run_outreach_agent(lead_dict, analysis_dict)

    assert result["chosen_channel"] == "deferred"
    assert result["requires_human_review"] is True
