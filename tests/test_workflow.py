import json
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


async def test_run_agent_returns_200_with_correct_structure():
    lead = _make_lead()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
    ])

    plan = {"actions": ["mark_needs_review"], "requires_human_review": True, "reasoning_summary": "Needs review"}

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-agent")

    assert response.status_code == 200
    data = response.json()
    assert data["lead_id"] == 1
    assert "plan" in data
    assert "actions_executed" in data
    assert "results" in data
    assert "metrics" in data


async def test_run_agent_returns_404_for_missing_lead():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(None))

    async with _client_with_db(mock_db) as client:
        response = await client.post("/leads/999/run-agent")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


async def test_actions_filtered_to_allowed_only():
    lead = _make_lead()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
    ])

    plan = {
        "actions": ["mark_needs_review", "delete_crm_records", "send_spam"],
        "requires_human_review": True,
        "reasoning_summary": "Testing filter",
    }

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-agent")

    assert response.status_code == 200
    data = response.json()
    assert "delete_crm_records" not in data["actions_executed"]
    assert "send_spam" not in data["actions_executed"]
    assert "mark_needs_review" in data["actions_executed"]


async def test_agent_json_failure_returns_fallback_and_200():
    lead = _make_lead()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
    ])

    bad_response = MagicMock()
    bad_response.content = [MagicMock()]
    bad_response.content[0].text = "not valid json {{ at all"

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=bad_response)

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-agent")

    assert response.status_code == 200
    data = response.json()
    assert data["plan"]["requires_human_review"] is True
    assert "mark_needs_review" in data["plan"]["actions"]


async def test_mark_needs_review_updates_lead_status():
    lead = _make_lead(status="new")
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
    ])

    plan = {"actions": ["mark_needs_review"], "requires_human_review": True, "reasoning_summary": "Flagging"}

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        async with _client_with_db(mock_db) as client:
            await client.post("/leads/1/run-agent")

    assert lead.status == "needs_review"


async def test_skip_outreach_updates_lead_status():
    lead = _make_lead(status="new")
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
    ])

    plan = {"actions": ["skip_outreach"], "requires_human_review": False, "reasoning_summary": "Skipping"}

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        async with _client_with_db(mock_db) as client:
            await client.post("/leads/1/run-agent")

    assert lead.status == "skipped"


async def test_metrics_row_created_with_correct_fields():
    lead = _make_lead()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
    ])

    plan = {"actions": ["mark_needs_review"], "requires_human_review": True, "reasoning_summary": "Flagging"}
    added_objects = []
    mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-agent")

    assert response.status_code == 200
    from app.models.metrics import AutomationMetrics
    metrics_rows = [obj for obj in added_objects if isinstance(obj, AutomationMetrics)]
    assert len(metrics_rows) == 1
    assert metrics_rows[0].lead_id == 1
    assert metrics_rows[0].workflow_name == "gtm_workflow"


async def test_analyze_executes_before_generate_outreach():
    lead = _make_lead()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),
        _scalar_result(None),
    ])

    plan = {
        "actions": ["analyze_lead", "generate_outreach"],
        "requires_human_review": False,
        "reasoning_summary": "Analyze then generate",
    }

    execution_order = []

    async def mock_analyze(lead):
        execution_order.append("analyze_lead")
        return _ANALYSIS_DICT

    async def mock_generate(lead, analysis):
        execution_order.append("generate_outreach")
        return _OUTREACH_DICT

    with patch("app.agents.gtm_workflow_agent.AsyncAnthropic") as mock_cls, \
         patch("app.routers.workflow.ai_service.analyze_lead", side_effect=mock_analyze), \
         patch("app.routers.workflow.outreach_service.generate_outreach", side_effect=mock_generate):
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=_agent_response(plan))

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-agent")

    assert response.status_code == 200
    assert execution_order.index("analyze_lead") < execution_order.index("generate_outreach")
