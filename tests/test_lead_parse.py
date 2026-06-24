import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import app

_PARSED_LEAD = {
    "first_name": "Sarah",
    "last_name": "Chen",
    "email": "s@acme.io",
    "company": "Acme",
    "title": "VP",
    "phone_number": None,
    "city": None,
    "state": None,
    "country": None,
    "notes": None,
}


@asynccontextmanager
async def _test_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test 1: POST /leads/parse returns 200 with valid text and mocked service
# ---------------------------------------------------------------------------
async def test_parse_endpoint_returns_200_with_valid_text():
    # The endpoint does a local import, so we patch at the service module level
    with patch(
        "app.services.lead_parse_service.parse_lead_from_text",
        new=AsyncMock(return_value=_PARSED_LEAD),
    ):
        async with _test_client() as client:
            response = await client.post(
                "/leads/parse",
                json={"raw_text": "Sarah Chen s@acme.io Acme Corp VP of Sales"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "s@acme.io"
    assert data["first_name"] == "Sarah"


# ---------------------------------------------------------------------------
# Test 2: POST /leads/parse returns 422 when parsed email is None
# ---------------------------------------------------------------------------
async def test_parse_endpoint_returns_422_when_email_missing():
    no_email_result = {**_PARSED_LEAD, "email": None}
    with patch(
        "app.services.lead_parse_service.parse_lead_from_text",
        new=AsyncMock(return_value=no_email_result),
    ):
        async with _test_client() as client:
            response = await client.post(
                "/leads/parse",
                json={"raw_text": "Some valid raw text without email"},
            )

    assert response.status_code == 422
    assert "email address" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test 3: POST /leads/parse returns 422 for short input (Pydantic min_length)
# ---------------------------------------------------------------------------
async def test_parse_endpoint_returns_422_for_short_input():
    async with _test_client() as client:
        response = await client.post(
            "/leads/parse",
            json={"raw_text": "hi"},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 4: Service returns fallback dict on Anthropic exception
# ---------------------------------------------------------------------------
async def test_service_returns_fallback_on_anthropic_exception():
    from app.services.lead_parse_service import parse_lead_from_text

    # The try/except in the service wraps client.messages.create, not the
    # AsyncAnthropic() constructor call. Patch the instance so messages.create
    # raises inside the try block.
    mock_messages = AsyncMock()
    mock_messages.create = AsyncMock(side_effect=Exception("API error"))
    mock_client = MagicMock()
    mock_client.messages = mock_messages

    with patch(
        "app.services.lead_parse_service.AsyncAnthropic",
        return_value=mock_client,
    ):
        result = await parse_lead_from_text("some valid text here that is long enough")

    assert "parse_error" in result
    # Should not raise — graceful fallback
    assert result.get("email") is None


# ---------------------------------------------------------------------------
# Test 5: Service correctly parses JSON response from Anthropic
# ---------------------------------------------------------------------------
async def test_service_parses_json_input():
    from app.services.lead_parse_service import parse_lead_from_text

    fake_json = json.dumps({
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
        "company": "Example Inc",
        "title": "CTO",
        "phone_number": None,
        "city": None,
        "state": None,
        "country": None,
        "notes": None,
    })

    fake_content = MagicMock()
    fake_content.text = fake_json

    fake_response = MagicMock()
    fake_response.content = [fake_content]

    mock_messages = AsyncMock()
    mock_messages.create = AsyncMock(return_value=fake_response)

    mock_client = MagicMock()
    mock_client.messages = mock_messages

    with patch(
        "app.services.lead_parse_service.AsyncAnthropic",
        return_value=mock_client,
    ):
        result = await parse_lead_from_text('{"email": "jane@example.com", "first_name": "Jane"}')

    assert result["email"] == "jane@example.com"
    assert "parse_error" not in result
