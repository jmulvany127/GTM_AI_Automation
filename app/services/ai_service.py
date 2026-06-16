import json
import logging
from anthropic import AsyncAnthropic
from app.config import get_settings

_logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a B2B sales intelligence assistant. Analyze the lead information provided "
    "and return ONLY a valid JSON object with no explanation, preamble, or markdown fences.\n\n"
    "Use cautious, conservative language. Do not invent specific facts about the company. "
    "When signal is weak, default to low scores.\n\n"
    "Return exactly this JSON structure:\n"
    '{\n'
    '  "company_summary": "<brief factual description based only on provided info, or null>",\n'
    '  "persona_type": "<buyer persona type, or null>",\n'
    '  "pain_points": "<likely pain points based on role/industry, or null>",\n'
    '  "buying_signals": "<positive signals from notes/source, or null>",\n'
    '  "objections": "<likely objections, or null>",\n'
    '  "fit_score": <integer 0-100>,\n'
    '  "urgency_score": <integer 0-100>,\n'
    '  "overall_score": <integer 0-100>,\n'
    '  "recommended_action": "<next best action string, or null>",\n'
    '  "confidence_score": <float 0.0-1.0>\n'
    "}\n\n"
    "All score fields are required integers. confidence_score is a required float. "
    "Return only JSON, nothing else."
)

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
        result = json.loads(raw_text)
        result["raw_ai_json"] = raw_text
        return result
    except (json.JSONDecodeError, TypeError):
        return {**_FALLBACK, "raw_ai_json": raw_text}
