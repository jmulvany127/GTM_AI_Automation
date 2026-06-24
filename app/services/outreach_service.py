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
    KEY_PAIN_POINTS_WE_SOLVE,
    SENDER_TITLE,
)

_logger = logging.getLogger(__name__)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


_SYSTEM_PROMPT = f"""You are the outreach content writer for {COMPANY_NAME}, {COMPANY_LOCATION}.

ABOUT THE COMPANY:
{COMPANY_DESCRIPTION}

PRODUCT:
{PRODUCT_DESCRIPTION}

VALUE PROPOSITION:
{VALUE_PROPOSITION}

IDEAL CUSTOMER PROFILE:
{TARGET_CUSTOMER}

PAIN POINTS WE SOLVE:
{KEY_PAIN_POINTS_WE_SOLVE}

You are writing outreach on behalf of {COMPANY_NAME} to multifamily real estate operators. Every email and LinkedIn message must be written as a {COMPANY_NAME} representative reaching out to a prospect. Reference specific {COMPANY_NAME} value propositions where they match the lead's pain points. Never use generic GTM language — always be specific to {COMPANY_NAME} and the multifamily industry.

The sender is {USER_FULL_NAME} ({USER_EMAIL}), {SENDER_TITLE} at {COMPANY_NAME}.
Email signatures must read: {USER_FULL_NAME} | {SENDER_TITLE} | {COMPANY_NAME}
LinkedIn messages must be written from the perspective of a {COMPANY_NAME} GTM Engineer connecting with a multifamily operator.
Never output bracketed placeholders such as [Company Name], [Your Product], [Your Name], [Sender], or any similar bracketed text — you always know you are representing {COMPANY_NAME}.

Using the lead data and analysis provided, write personalised outreach content — not generic templates. Reference specific details from the lead's role, company, and pain points.

Return ONLY a valid JSON object with no explanation, preamble, or markdown fences.

Return exactly this JSON structure:
{{
  "subject": "<compelling email subject line>",
  "email_body": "<personalised cold email, under 130 words>",
  "follow_up_email": "<shorter follow-up email, under 90 words>",
  "linkedin_message": "<LinkedIn connection message, strictly no more than 280 characters — complete, professional, and ready to send. Do not truncate mid-sentence. If you cannot fit a complete message in 280 characters, write a shorter complete message>",
  "call_notes": "<suggested talking points and questions for a discovery call>"
}}

All fields are required. Return only JSON, nothing else."""

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
                max_tokens=1500,
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
