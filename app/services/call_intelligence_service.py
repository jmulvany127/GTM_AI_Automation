import json
import logging
import re
from anthropic import AsyncAnthropic
from app.config import get_settings, USER_FULL_NAME, USER_EMAIL

_logger = logging.getLogger(__name__)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_SYSTEM_PROMPT = (
    "you are an expert sales intelligence analyst. Read the call transcript and extract "
    "structured intelligence. Return ONLY valid JSON with these exact keys: title "
    "(concise call name, max 60 chars, e.g. \"Discovery call with Sarah Chen — Greystar\"), "
    "description (1-2 sentences summarising call context), pain_points, "
    "objections, competitors, budget_signals, decision_timeline, buying_intent_score "
    "(float 0.0-10.0), recommended_follow_up, crm_note, follow_up_email. Be concise. "
    "If a field has no evidence in the transcript return null. "
    f"The sender's name is {USER_FULL_NAME} and their email is {USER_EMAIL}. "
    "Use this name in follow_up_email sign-offs and anywhere a sender name appears. "
    "Never output bracketed placeholders such as [Your Name], [Name], [Sender], "
    "[your name], or any similar bracketed text — always use the real name provided."
)

_FALLBACK: dict = {
    "title": None,
    "description": None,
    "pain_points": None,
    "objections": None,
    "competitors": None,
    "budget_signals": None,
    "decision_timeline": None,
    "buying_intent_score": None,
    "recommended_follow_up": None,
    "crm_note": None,
    "follow_up_email": None,
    "fallback": True,
}


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


async def analyze_transcript(transcript: str) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    raw_text = None
    for attempt in range(2):
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": transcript}],
            )
            raw_text = response.content[0].text
            break
        except Exception as exc:
            _logger.warning("Anthropic API call failed (attempt %d/2): %s", attempt + 1, exc)
            if attempt == 1:
                return {**_FALLBACK}

    try:
        result = json.loads(_extract_json(raw_text))
        return result
    except (json.JSONDecodeError, TypeError) as exc:
        _logger.warning("Failed to parse Anthropic response: %s", exc)
        return {**_FALLBACK}
