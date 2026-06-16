import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_service import analyze_lead


def _make_lead(**kwargs):
    defaults = dict(
        first_name="Jane", last_name="Smith",
        company="Acme Corp", job_title="VP Sales",
        company_website="acme.com", source="LinkedIn",
        notes="Interested in automation",
    )
    defaults.update(kwargs)
    lead = MagicMock()
    for k, v in defaults.items():
        setattr(lead, k, v)
    return lead


def _mock_anthropic_response(text: str):
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


_VALID_JSON_TEXT = json.dumps({
    "company_summary": "A sales enablement company",
    "persona_type": "Champion",
    "pain_points": "Manual sales processes",
    "buying_signals": "Requested a demo",
    "objections": "Budget concerns",
    "fit_score": 80,
    "urgency_score": 60,
    "overall_score": 70,
    "recommended_action": "Schedule discovery call",
    "confidence_score": 0.85,
})


async def test_analyze_lead_returns_correct_structure():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(_VALID_JSON_TEXT)
        )
        result = await analyze_lead(_make_lead())

    assert result["fit_score"] == 80
    assert result["urgency_score"] == 60
    assert result["overall_score"] == 70
    assert result["confidence_score"] == 0.85
    assert result["persona_type"] == "Champion"
    assert result["raw_ai_json"] == _VALID_JSON_TEXT


async def test_analyze_lead_malformed_json_returns_fallback():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response("not valid json {{{{")
        )
        result = await analyze_lead(_make_lead())

    assert result["fit_score"] == 0
    assert result["urgency_score"] == 0
    assert result["overall_score"] == 0
    assert result["confidence_score"] == 0.0
    assert result["company_summary"] is None
    assert result["raw_ai_json"] == "not valid json {{{{"


async def test_analyze_lead_exception_retries_once_then_fallback():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(side_effect=Exception("API unavailable"))

        result = await analyze_lead(_make_lead())

    assert instance.messages.create.call_count == 2
    assert result["fit_score"] == 0
    assert result["confidence_score"] == 0.0


async def test_score_fields_are_integers_in_range():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(_VALID_JSON_TEXT)
        )
        result = await analyze_lead(_make_lead())

    assert isinstance(result["fit_score"], int)
    assert isinstance(result["urgency_score"], int)
    assert isinstance(result["overall_score"], int)
    assert 0 <= result["fit_score"] <= 100
    assert 0 <= result["urgency_score"] <= 100
    assert 0 <= result["overall_score"] <= 100


async def test_confidence_score_is_float_in_range():
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(_VALID_JSON_TEXT)
        )
        result = await analyze_lead(_make_lead())

    assert isinstance(result["confidence_score"], float)
    assert 0.0 <= result["confidence_score"] <= 1.0


async def test_analyze_lead_handles_json_in_markdown_code_fence():
    # Claude sometimes wraps its JSON in ```json ... ``` despite being told not to.
    # The service must strip fences before parsing — not return the fallback.
    fenced = f"```json\n{_VALID_JSON_TEXT}\n```"
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(fenced)
        )
        result = await analyze_lead(_make_lead())

    assert result["fit_score"] == 80
    assert result["persona_type"] == "Champion"
    assert result["confidence_score"] == 0.85
    # raw_ai_json must preserve the original text including fences (for debugging)
    assert result["raw_ai_json"] == fenced


async def test_analyze_lead_handles_json_in_plain_code_fence():
    # Same as above but without the 'json' language specifier.
    fenced = f"```\n{_VALID_JSON_TEXT}\n```"
    with patch("app.services.ai_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(fenced)
        )
        result = await analyze_lead(_make_lead())

    assert result["fit_score"] == 80
    assert result["confidence_score"] == 0.85
    assert result["raw_ai_json"] == fenced
