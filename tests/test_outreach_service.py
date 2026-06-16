import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.outreach_service import generate_outreach


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


def _make_analysis(**kwargs):
    defaults = dict(
        persona_type="Champion",
        pain_points="Manual sales processes",
        buying_signals="Requested a demo",
        recommended_action="Schedule discovery call",
        overall_score=75,
    )
    defaults.update(kwargs)
    analysis = MagicMock()
    for k, v in defaults.items():
        setattr(analysis, k, v)
    return analysis


def _mock_anthropic_response(text: str):
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


_VALID_JSON_TEXT = json.dumps({
    "subject": "Automate your sales pipeline, Jane",
    "email_body": "Hi Jane, I noticed Acme Corp is scaling its sales team. We help VP Sales leaders eliminate manual pipeline work so reps spend more time selling. Worth a 20-minute call?",
    "follow_up_email": "Hi Jane, just circling back on my last note. Would a quick call this week work to explore if we can help Acme Corp?",
    "linkedin_message": "Hi Jane, saw you're leading sales at Acme Corp — we help sales leaders cut manual work. Happy to share how. Worth connecting?",
    "call_notes": "Ask about current CRM setup. Explore pain around manual reporting. Understand team size and growth plans.",
})


async def test_generate_outreach_returns_correct_structure():
    with patch("app.services.outreach_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(_VALID_JSON_TEXT)
        )
        result = await generate_outreach(_make_lead(), _make_analysis())

    assert isinstance(result["subject"], str)
    assert isinstance(result["email_body"], str)
    assert isinstance(result["follow_up_email"], str)
    assert isinstance(result["linkedin_message"], str)
    assert isinstance(result["call_notes"], str)


async def test_generate_outreach_malformed_json_returns_fallback():
    with patch("app.services.outreach_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response("not valid json {{{{")
        )
        result = await generate_outreach(_make_lead(), _make_analysis())

    assert result["subject"] is None
    assert result["email_body"] is None
    assert result["follow_up_email"] is None
    assert result["linkedin_message"] is None
    assert result["call_notes"] is None


async def test_generate_outreach_exception_retries_once_then_fallback():
    with patch("app.services.outreach_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(side_effect=Exception("API unavailable"))

        result = await generate_outreach(_make_lead(), _make_analysis())

    assert instance.messages.create.call_count == 2
    assert result["subject"] is None
    assert result["email_body"] is None


async def test_generate_outreach_handles_json_in_markdown_code_fence():
    fenced = f"```json\n{_VALID_JSON_TEXT}\n```"
    with patch("app.services.outreach_service.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages = MagicMock()
        instance.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(fenced)
        )
        result = await generate_outreach(_make_lead(), _make_analysis())

    assert isinstance(result["subject"], str)
    assert isinstance(result["email_body"], str)
