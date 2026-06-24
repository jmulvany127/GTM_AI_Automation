import json
import logging
import re
from anthropic import AsyncAnthropic
from app.config import get_settings

_logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_SYSTEM_PROMPT = """You are a lead data extraction specialist. Your job is to read any format of input — plain text, JSON, LinkedIn profiles, email signatures, business card text, CRM exports, or free-form notes — and extract lead information.

Return ONLY valid JSON with these exact keys: first_name, last_name, email, company, title, phone_number, city, state, country, notes.

For any field you cannot find evidence of in the text, return null. Never invent or guess values that are not present or strongly implied by the input."""

_FALLBACK: dict = {
    "first_name": None,
    "last_name": None,
    "email": None,
    "company": None,
    "title": None,
    "phone_number": None,
    "city": None,
    "state": None,
    "country": None,
    "notes": None,
    "parse_error": "AI parsing failed — please enter lead details manually.",
}

_EXPECTED_KEYS = {
    "first_name", "last_name", "email", "company", "title",
    "phone_number", "city", "state", "country", "notes",
}


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


async def parse_lead_from_text(raw_text: str) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_text}],
        )
        raw_response_text = response.content[0].text
        parsed = json.loads(_extract_json(raw_response_text))
        return {key: parsed.get(key) for key in _EXPECTED_KEYS}
    except Exception as exc:
        _logger.warning("Lead parse service failed: %s", exc)
        return {**_FALLBACK}
