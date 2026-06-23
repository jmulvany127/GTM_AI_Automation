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

# Combined agent result — all content + decision keys in one dict
_COMBINED_AGENT_RESULT = {
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


# ---------------------------------------------------------------------------
# Test 1: POST /leads/{id}/run-outreach-agent returns 200 with correct shape
# ---------------------------------------------------------------------------

async def test_run_outreach_agent_returns_200_with_correct_shape():
    lead = _make_lead()
    analysis = _make_analysis()

    mock_db = AsyncMock()
    # Execute call order: (1) lead, (2) existing_log (None), (3) analysis, (4) crm_sync (None)
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),    # no existing log
        _scalar_result(analysis),
        _scalar_result(None),    # no CRM sync
    ])
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("app.routers.leads.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.leads.slack_service.send_alert", new_callable=AsyncMock):
        mock_agent.return_value = _COMBINED_AGENT_RESULT.copy()

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 200
    data = response.json()

    # Content keys
    assert "subject" in data
    assert "email_body" in data
    assert "follow_up_email" in data
    assert "linkedin_message" in data
    assert "call_notes" in data

    # Decision keys
    assert "chosen_channel" in data
    assert "agent_reasoning" in data
    assert "requires_human_review" in data
    assert "review_reason" in data
    assert "execution_status" in data

    # Spot-check specific values from _COMBINED_AGENT_RESULT
    assert data["chosen_channel"] == "email"
    assert data["agent_reasoning"] == "Email is best."
    assert data["requires_human_review"] is False


# ---------------------------------------------------------------------------
# Test 2: OutreachMessage record is created by the outreach agent run
# ---------------------------------------------------------------------------

async def test_outreach_message_created_by_agent_run():
    from app.models.outreach import OutreachMessage

    lead = _make_lead()
    analysis = _make_analysis()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),    # no existing log
        _scalar_result(analysis),
        _scalar_result(None),    # no CRM sync
    ])
    mock_db.add = MagicMock()    # db.add is sync
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("app.routers.leads.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.leads.slack_service.send_alert", new_callable=AsyncMock):
        mock_agent.return_value = _COMBINED_AGENT_RESULT.copy()

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 200

    add_calls = mock_db.add.call_args_list
    outreach_calls = [c for c in add_calls if isinstance(c.args[0], OutreachMessage)]
    assert len(outreach_calls) == 1


# ---------------------------------------------------------------------------
# Test 3: OutreachExecutionLog created with correct channel decision
# ---------------------------------------------------------------------------

async def test_execution_log_created_with_correct_channel():
    from app.models.outreach_execution_log import OutreachExecutionLog

    lead = _make_lead()
    analysis = _make_analysis()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),    # no existing log
        _scalar_result(analysis),
        _scalar_result(None),    # no CRM sync
    ])
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()

    agent_result = {**_COMBINED_AGENT_RESULT, "chosen_channel": "email"}

    with patch("app.routers.leads.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.leads.slack_service.send_alert", new_callable=AsyncMock):
        mock_agent.return_value = agent_result

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 200

    add_calls = mock_db.add.call_args_list
    log_calls = [c for c in add_calls if isinstance(c.args[0], OutreachExecutionLog)]
    assert len(log_calls) == 1
    assert log_calls[0].args[0].chosen_channel == "email"


# ---------------------------------------------------------------------------
# Test 4: Service fallback on exception returns all keys
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

    assert result["fallback"] is True
    assert result["requires_human_review"] is True
    assert result["chosen_channel"] == "deferred"

    # All 5 content keys must be present (even if None)
    for key in ("subject", "email_body", "follow_up_email", "linkedin_message", "call_notes"):
        assert key in result


# ---------------------------------------------------------------------------
# Test 5: Gmail called when channel is email and requires_human_review is False
# ---------------------------------------------------------------------------

async def test_gmail_called_when_channel_is_email_and_no_review():
    from app.services import gmail_service

    lead = _make_lead()
    analysis = _make_analysis()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),    # no existing log
        _scalar_result(analysis),
        _scalar_result(None),    # no CRM sync
    ])
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()

    agent_result = {**_COMBINED_AGENT_RESULT, "chosen_channel": "email", "requires_human_review": False}

    with patch("app.routers.leads.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.leads.asyncio.to_thread", new_callable=AsyncMock) as mock_thread, \
         patch("app.routers.leads.slack_service.send_alert", new_callable=AsyncMock):
        mock_agent.return_value = agent_result
        mock_thread.return_value = True  # simulates sent=True

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 200
    mock_thread.assert_called_once()
    assert mock_thread.call_args.args[0] == gmail_service.send_email


# ---------------------------------------------------------------------------
# Test 6: Gmail NOT called when requires_human_review is True
# ---------------------------------------------------------------------------

async def test_gmail_not_called_when_review_required():
    lead = _make_lead()
    analysis = _make_analysis()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),    # no existing log
        _scalar_result(analysis),
        _scalar_result(None),    # no CRM sync
    ])
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()

    agent_result = {**_COMBINED_AGENT_RESULT, "requires_human_review": True, "review_reason": "Low score"}

    with patch("app.routers.leads.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.leads.asyncio.to_thread", new_callable=AsyncMock) as mock_thread, \
         patch("app.routers.leads.slack_service.send_alert", new_callable=AsyncMock):
        mock_agent.return_value = agent_result

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 200
    mock_thread.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: Slack called when score is >= 70
# ---------------------------------------------------------------------------

async def test_slack_called_when_score_is_7_or_above():
    lead = _make_lead()
    analysis = _make_analysis(overall_score=78)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),    # no existing log
        _scalar_result(analysis),
        _scalar_result(None),    # no CRM sync
    ])
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    mock_db.commit = AsyncMock()

    agent_result = {**_COMBINED_AGENT_RESULT, "chosen_channel": "email", "requires_human_review": False}

    with patch("app.routers.leads.run_outreach_agent", new_callable=AsyncMock) as mock_agent, \
         patch("app.routers.leads.asyncio.to_thread", new_callable=AsyncMock) as mock_thread, \
         patch("app.routers.leads.slack_service.send_alert", new_callable=AsyncMock) as mock_slack:
        mock_agent.return_value = agent_result
        mock_thread.return_value = True  # email sent OK

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/run-outreach-agent")

    assert response.status_code == 200
    mock_slack.assert_called_once()


# ---------------------------------------------------------------------------
# Test 8: Deterministic override — personal email domain forces deferred + review
# ---------------------------------------------------------------------------

async def test_deterministic_override_personal_email_forces_deferred():
    from app.services.outreach_agent_service import run_outreach_agent

    llm_response = {
        "subject": "Hello", "email_body": "Body.", "follow_up_email": "FU.",
        "linkedin_message": "LI.", "call_notes": "Notes.",
        "chosen_channel": "both", "requires_human_review": False,
        "review_reason": None, "agent_reasoning": "test", "personalisation_notes": None,
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
