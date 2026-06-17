import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("HUBSPOT_ACCESS_TOKEN", "test-hs-token")

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db
from app.models.crm_log import CrmSyncLog

_NOW = datetime(2026, 6, 17, 12, 0, 0)


def _make_lead(**kwargs):
    defaults = dict(
        id=1, first_name="Jane", last_name="Smith",
        email="jane@example.com", company="Acme Corp",
        job_title="VP Sales", company_website="acme.com",
        status="analyzed",
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_analysis(**kwargs):
    defaults = dict(
        id=1, lead_id=1,
        persona_type="Champion", pain_points="Manual work",
        buying_signals="Demo requested", objections=None,
        fit_score=80, urgency_score=70, overall_score=78,
        recommended_action="Schedule call",
        confidence_score=0.85, raw_ai_json=None,
        created_at=_NOW,
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_crm_log(**kwargs):
    defaults = dict(
        id=1, lead_id=1, crm_system="hubspot",
        sync_status="success", external_contact_id="hs-123",
        error_message=None, created_at=_NOW,
    )
    defaults.update(kwargs)
    m = MagicMock(spec=CrmSyncLog)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _scalar_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


async def _refresh_obj(obj):
    """Simulate DB refresh by populating server-generated fields."""
    from app.models.crm_log import CrmSyncLog as _CrmSyncLog
    if isinstance(obj, _CrmSyncLog):
        if obj.id is None:
            obj.id = 1
        if obj.crm_system is None:
            obj.crm_system = "hubspot"
        if obj.created_at is None:
            obj.created_at = _NOW


@asynccontextmanager
async def _client_with_db(mock_session):
    async def _override():
        yield mock_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _hs_response(data: dict, status_code: int = 200) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.json.return_value = data
    r.text = str(data)
    return r


async def test_sync_hubspot_returns_200_with_crm_log_structure():
    lead = _make_lead()
    analysis = _make_analysis()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),  # outreach
    ])
    log = _make_crm_log()
    mock_db.refresh = AsyncMock(side_effect=_refresh_obj)

    with patch("app.routers.hubspot.hubspot_service.create_or_update_contact", new=AsyncMock(return_value="hs-123")), \
         patch("app.routers.hubspot.hubspot_service.create_note", new=AsyncMock(return_value="note-1")), \
         patch("app.routers.hubspot.hubspot_service.create_task", new=AsyncMock(return_value="task-1")):

        added = []
        mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/sync-hubspot")

    assert response.status_code == 200
    data = response.json()
    for field in ("id", "lead_id", "crm_system", "sync_status", "external_contact_id", "error_message", "created_at"):
        assert field in data


async def test_sync_hubspot_returns_404_when_lead_not_found():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(None))

    async with _client_with_db(mock_db) as client:
        response = await client.post("/leads/999/sync-hubspot")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


async def test_sync_hubspot_returns_404_when_no_analysis():
    lead = _make_lead()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(None),  # no analysis
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.post("/leads/1/sync-hubspot")

    assert response.status_code == 404
    assert response.json()["detail"] == "No analysis found for this lead"


async def test_sync_status_is_success_when_hubspot_calls_succeed():
    lead = _make_lead()
    analysis = _make_analysis()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),
    ])

    added = []
    mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    mock_db.refresh = AsyncMock(side_effect=_refresh_obj)

    with patch("app.routers.hubspot.hubspot_service.create_or_update_contact", new=AsyncMock(return_value="hs-456")), \
         patch("app.routers.hubspot.hubspot_service.create_note", new=AsyncMock(return_value="note-2")):

        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/sync-hubspot")

    assert response.status_code == 200
    crm_logs = [o for o in added if isinstance(o, CrmSyncLog)]
    assert len(crm_logs) == 1
    assert crm_logs[0].sync_status == "success"
    assert crm_logs[0].external_contact_id == "hs-456"


async def test_sync_status_is_failed_and_error_message_populated_on_exception():
    lead = _make_lead()
    analysis = _make_analysis()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),
    ])

    added = []
    mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    mock_db.refresh = AsyncMock(side_effect=_refresh_obj)

    with patch(
        "app.routers.hubspot.hubspot_service.create_or_update_contact",
        new=AsyncMock(side_effect=RuntimeError("HubSpot API error 401: Unauthorized")),
    ):
        async with _client_with_db(mock_db) as client:
            response = await client.post("/leads/1/sync-hubspot")

    assert response.status_code == 200
    crm_logs = [o for o in added if isinstance(o, CrmSyncLog)]
    assert len(crm_logs) == 1
    assert crm_logs[0].sync_status == "failed"
    assert "401" in crm_logs[0].error_message


async def test_crm_log_always_created_on_success():
    lead = _make_lead()
    analysis = _make_analysis()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),
    ])
    added = []
    mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    mock_db.refresh = AsyncMock(side_effect=_refresh_obj)

    with patch("app.routers.hubspot.hubspot_service.create_or_update_contact", new=AsyncMock(return_value="c1")), \
         patch("app.routers.hubspot.hubspot_service.create_note", new=AsyncMock(return_value="n1")):
        async with _client_with_db(mock_db) as client:
            await client.post("/leads/1/sync-hubspot")

    crm_logs = [o for o in added if isinstance(o, CrmSyncLog)]
    assert len(crm_logs) == 1


async def test_crm_log_always_created_on_failure():
    lead = _make_lead()
    analysis = _make_analysis()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),
    ])
    added = []
    mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    mock_db.refresh = AsyncMock(side_effect=_refresh_obj)

    with patch(
        "app.routers.hubspot.hubspot_service.create_or_update_contact",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        async with _client_with_db(mock_db) as client:
            await client.post("/leads/1/sync-hubspot")

    crm_logs = [o for o in added if isinstance(o, CrmSyncLog)]
    assert len(crm_logs) == 1


async def test_create_task_called_when_overall_score_gte_85():
    lead = _make_lead()
    analysis = _make_analysis(overall_score=90)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),
    ])
    added = []
    mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    mock_db.refresh = AsyncMock(side_effect=_refresh_obj)

    mock_create_task = AsyncMock(return_value="task-99")
    with patch("app.routers.hubspot.hubspot_service.create_or_update_contact", new=AsyncMock(return_value="c9")), \
         patch("app.routers.hubspot.hubspot_service.create_note", new=AsyncMock(return_value="n9")), \
         patch("app.routers.hubspot.hubspot_service.create_task", new=mock_create_task):
        async with _client_with_db(mock_db) as client:
            await client.post("/leads/1/sync-hubspot")

    mock_create_task.assert_called_once()


async def test_create_task_not_called_when_overall_score_lt_85():
    lead = _make_lead()
    analysis = _make_analysis(overall_score=70)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(lead),
        _scalar_result(analysis),
        _scalar_result(None),
    ])
    added = []
    mock_db.add = MagicMock(side_effect=lambda obj: added.append(obj))
    mock_db.refresh = AsyncMock(side_effect=_refresh_obj)

    mock_create_task = AsyncMock(return_value="task-skip")
    with patch("app.routers.hubspot.hubspot_service.create_or_update_contact", new=AsyncMock(return_value="c8")), \
         patch("app.routers.hubspot.hubspot_service.create_note", new=AsyncMock(return_value="n8")), \
         patch("app.routers.hubspot.hubspot_service.create_task", new=mock_create_task):
        async with _client_with_db(mock_db) as client:
            await client.post("/leads/1/sync-hubspot")

    mock_create_task.assert_not_called()


async def test_hubspot_sync_success_rate_returns_correct_ratio():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        _scalar_result(5),    # total_leads_processed
        _scalar_result(3),    # high_priority_leads
        _scalar_result(125.0),
        _scalar_result(30.5),
        _scalar_result(72.4),
        _scalar_result(4),    # success crm logs
        _scalar_result(5),    # total crm logs
    ])

    async with _client_with_db(mock_db) as client:
        response = await client.get("/metrics/roi")

    assert response.status_code == 200
    data = response.json()
    assert data["hubspot_sync_success_rate"] == 0.8
