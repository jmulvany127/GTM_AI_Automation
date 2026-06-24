import json
import logging
import re
from anthropic import AsyncAnthropic
from app.config import (
    get_settings,
    COMPANY_NAME,
    COMPANY_LOCATION,
    COMPANY_DESCRIPTION,
    PRODUCT_DESCRIPTION,
    VALUE_PROPOSITION,
    TARGET_CUSTOMER,
    KEY_INTEGRATIONS,
    KEY_PAIN_POINTS_WE_SOLVE,
)

_logger = logging.getLogger(__name__)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(text: str) -> str:
    """Strip markdown code fences if Claude wrapped its response in them."""
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()

_SYSTEM_PROMPT = f"""You are the lead analysis agent for {COMPANY_NAME}, {COMPANY_LOCATION}.

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

Analyse the lead information provided and score their fit for {COMPANY_NAME} specifically — not for a generic B2B product.

SCORING GUIDELINES:
- A high fit score (80-100) means this lead is an ideal customer for {COMPANY_NAME}: a multifamily operator managing 1,000+ units, evaluating PropTech, with pain points {COMPANY_NAME} directly solves (slow leasing response, manual qualification, inconsistent follow-up, poor PMS reporting, renewal gaps).
- A low fit score (0-40) means this lead is unlikely to benefit from or purchase {COMPANY_NAME} — wrong industry, too small, or no relevant pain points.
- Pain points extracted should be evaluated against {COMPANY_NAME}'s known pain points. Pain points that match what {COMPANY_NAME} solves should increase the fit score.
- Buying signals should be evaluated in the context of multifamily PropTech purchasing behaviour — urgency, budget authority, active evaluation, and integration requirements are strong signals.
- Recommended actions should reference what a {COMPANY_NAME} GTM team would do next (e.g. book a demo, send Yardi integration overview, propose 30-day pilot, share ROI case study).

Use cautious, conservative language. Do not invent specific facts about the company. When signal is weak, default to low scores.

Return ONLY a valid JSON object with no explanation, preamble, or markdown fences.

Return exactly this JSON structure:
{{
  "company_summary": "<brief factual description based only on provided info, or null>",
  "persona_type": "<buyer persona type, or null>",
  "pain_points": "<likely pain points based on role/industry, or null>",
  "buying_signals": "<positive signals from notes/source, or null>",
  "objections": "<likely objections, or null>",
  "fit_score": <integer 0-100>,
  "urgency_score": <integer 0-100>,
  "overall_score": <integer 0-100>,
  "recommended_action": "<next best action for the {COMPANY_NAME} GTM team, or null>",
  "confidence_score": <float 0.0-1.0>
}}

All score fields are required integers. confidence_score is a required float. Return only JSON, nothing else."""

_FALLBACK: dict = {
    "company_summary": None,
    "persona_type": None,
    "pain_points": None,
    "buying_signals": None,
    "objections": None,
    "fit_score": 0,
    "urgency_score": 0,
    "overall_score": 0,
    "recommended_action": None,
    "confidence_score": 0.0,
    "raw_ai_json": None,
}


async def analyze_lead(lead) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = (
        f"Name: {lead.first_name} {lead.last_name}\n"
        f"Company: {lead.company or 'Unknown'}\n"
        f"Job Title: {lead.job_title or 'Unknown'}\n"
        f"Website: {lead.company_website or 'Unknown'}\n"
        f"Source: {lead.source or 'Unknown'}\n"
        f"Notes: {lead.notes or 'None'}"
    )

    raw_text = None
    for attempt in range(2):
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text = response.content[0].text
            break
        except Exception as exc:
            _logger.warning("Anthropic API call failed (attempt %d/2): %s", attempt + 1, exc)
            if attempt == 1:
                return {**_FALLBACK}

    try:
        result = json.loads(_extract_json(raw_text))
        result["raw_ai_json"] = raw_text
        return result
    except (json.JSONDecodeError, TypeError):
        return {**_FALLBACK, "raw_ai_json": raw_text}
