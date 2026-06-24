import json
import logging
import re
from anthropic import AsyncAnthropic
from app.config import get_settings, USER_FULL_NAME, USER_EMAIL

_logger = logging.getLogger(__name__)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


_SYSTEM_PROMPT = (
    "You are a B2B sales copywriter. Using the lead data and analysis provided, "
    "write personalised outreach content — not generic templates. "
    "Reference specific details from the lead's role, company, and pain points.\n\n"
    f"The sender's name is {USER_FULL_NAME} and their email is {USER_EMAIL}. "
    "Use this name in all sign-offs, signatures, and anywhere a sender name appears. "
    "Never output bracketed placeholders such as [Your Name], [Name], [Sender], "
    "[your name], or any similar bracketed text — always use the real name provided.\n\n"
    "Return ONLY a valid JSON object with no explanation, preamble, or markdown fences.\n\n"
    "Return exactly this JSON structure:\n"
    '{\n'
    '  "subject": "<compelling email subject line>",\n'
    '  "email_body": "<personalised cold email, under 130 words>",\n'
    '  "follow_up_email": "<shorter follow-up email, under 90 words>",\n'
    '  "linkedin_message": "<LinkedIn connection message, under 300 characters>",\n'
    '  "call_notes": "<suggested talking points and questions for a discovery call>"\n'
    "}\n\n"
    "All fields are required. Return only JSON, nothing else."
)

_FALLBACK: dict = {
    "subject": None,
    "email_body": None,
    "follow_up_email": None,
    "linkedin_message": None,
    "call_notes": None,
}


async def generate_outreach(lead, analysis) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = (
        f"Lead Information:\n"
        f"Name: {lead.first_name} {lead.last_name}\n"
        f"Company: {lead.company or 'Unknown'}\n"
        f"Job Title: {lead.job_title or 'Unknown'}\n"
        f"Website: {lead.company_website or 'Unknown'}\n"
        f"Source: {lead.source or 'Unknown'}\n"
        f"Notes: {lead.notes or 'None'}\n\n"
        f"Analysis:\n"
        f"Persona Type: {analysis.persona_type or 'Unknown'}\n"
        f"Pain Points: {analysis.pain_points or 'Unknown'}\n"
        f"Buying Signals: {analysis.buying_signals or 'None'}\n"
        f"Recommended Action: {analysis.recommended_action or 'Unknown'}\n"
        f"Overall Score: {analysis.overall_score or 0}/100"
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
        return json.loads(_extract_json(raw_text))
    except (json.JSONDecodeError, TypeError):
        return {**_FALLBACK}
