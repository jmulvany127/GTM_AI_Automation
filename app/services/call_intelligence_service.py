import json
import logging
import re
from anthropic import AsyncAnthropic
from app.config import (
    get_settings,
    USER_FULL_NAME,
    USER_EMAIL,
    COMPANY_NAME,
    COMPANY_LOCATION,
    COMPANY_DESCRIPTION,
    PRODUCT_DESCRIPTION,
    VALUE_PROPOSITION,
    TARGET_CUSTOMER,
    KEY_INTEGRATIONS,
    KEY_PAIN_POINTS_WE_SOLVE,
    SENDER_TITLE,
)

_logger = logging.getLogger(__name__)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_SYSTEM_PROMPT = f"""You are the call intelligence analyst for {COMPANY_NAME}, {COMPANY_LOCATION}.

ABOUT THE COMPANY:
{COMPANY_DESCRIPTION}

PRODUCT:
{PRODUCT_DESCRIPTION}

VALUE PROPOSITION:
{VALUE_PROPOSITION}

IDEAL CUSTOMER PROFILE:
{TARGET_CUSTOMER}

KEY INTEGRATIONS:
{KEY_INTEGRATIONS}

PAIN POINTS WE SOLVE:
{KEY_PAIN_POINTS_WE_SOLVE}

Read the call transcript and extract structured intelligence for the {COMPANY_NAME} GTM team.

EXTRACTION GUIDELINES:
- Pain points extracted from transcripts should be mapped against {COMPANY_NAME}'s known pain points where relevant. Clearly note when a prospect's pain maps to something {COMPANY_NAME} directly solves.
- When the prospect mentions a specific PMS (Yardi, RealPage, Entrata), recommended follow-up actions should reference {COMPANY_NAME}'s native integration with that system. For example, if the prospect mentions Yardi frustration, the recommended follow-up should reference {COMPANY_NAME}'s native Yardi integration.
- The follow-up email must be written by a {COMPANY_NAME} GTM Engineer and reference the specific pain points raised on the call. Sign off as: {USER_FULL_NAME} | {SENDER_TITLE} | {COMPANY_NAME}.
- The crm_note must include a footer on a new line: "Analysed by {COMPANY_NAME} GTM OS".
- Never output bracketed placeholders such as [Your Name], [Company Name], [Sender] — always use real values.

Return ONLY valid JSON with these exact keys: title (concise call name, max 60 chars, e.g. "Discovery call with Sarah Chen — Greystar"), description (1-2 sentences summarising call context), pain_points, objections, competitors, budget_signals, decision_timeline, buying_intent_score (float 0.0-10.0), recommended_follow_up, crm_note, follow_up_email. Be concise. If a field has no evidence in the transcript return null."""

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
