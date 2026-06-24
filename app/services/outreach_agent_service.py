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
    KEY_PAIN_POINTS_WE_SOLVE,
    USER_FULL_NAME,
    USER_EMAIL,
    SENDER_TITLE,
)

_logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_SYSTEM_PROMPT = f"""You are the Domino AI outreach specialist for {COMPANY_NAME}, {COMPANY_LOCATION}.

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

Your role is to BOTH write personalised outreach content AND decide the best channel for a given lead.
You own all outreach activity — you generate every content field and make the channel decision in a single response.

## Content Rules

### email_body
- Under 130 words, ready to send
- Personalised to the specific lead and their company based on the analysis provided
- Sign off with: {USER_FULL_NAME} | {SENDER_TITLE} | {COMPANY_NAME}
- Never use placeholder text like [Your Name] or [Company] — always use the real values above

### follow_up_email
- Under 90 words
- A concise follow-up to the initial email if no reply is received
- Sign off the same way: {USER_FULL_NAME} | {SENDER_TITLE} | {COMPANY_NAME}
- Never use placeholder text

### linkedin_message
- Strictly under 280 characters (this is a hard limit — count carefully)
- Must be a complete, professional sentence — never truncated mid-thought
- This message will be sent manually by a human so it must be polished and ready
- If you cannot write a complete, professional message under 280 characters, set this field to null

### subject
- Compelling, concise email subject line personalised to the lead

### call_notes
- Brief notes for a future discovery call if applicable — key questions to ask, angles to explore
- Can be null if not applicable

## Channel Decision Rules

### chosen_channel
- overall_score >= 80 → prefer "both" (email + LinkedIn)
- overall_score 60–79 → prefer "email"
- overall_score < 60 → "deferred" and set requires_human_review=true
- If linkedin_message you generated is null or empty → exclude LinkedIn; never choose "both" or "linkedin"
- Personal email domains (gmail.com, hotmail.com, yahoo.com, outlook.com) → "deferred" and requires_human_review=true

### Human Review Triggers
- confidence_score < 0.6 → requires_human_review=true
- overall_score < 60 → requires_human_review=true
- Personal email domain → requires_human_review=true
- When requires_human_review=true, populate review_reason with a brief explanation

### Persona Signals
- persona_type == "Champion" → LinkedIn is high priority; prefer "both" if score allows

## Output Format
Return ONLY a valid JSON object — no explanation, no markdown fences:
{{
  "subject": "<compelling email subject line>",
  "email_body": "<personalised email body, under 130 words, signed {USER_FULL_NAME} | {SENDER_TITLE} | {COMPANY_NAME}>",
  "follow_up_email": "<follow-up email, under 90 words, signed {USER_FULL_NAME} | {SENDER_TITLE} | {COMPANY_NAME}>",
  "linkedin_message": "<under 280 chars, complete sentence, or null>",
  "call_notes": "<discovery call notes or null>",
  "chosen_channel": "<email|linkedin|both|deferred>",
  "agent_reasoning": "<brief explanation of why this channel and review status was chosen>",
  "requires_human_review": false,
  "review_reason": "<null if no review needed, or brief reason>",
  "personalisation_notes": "<optional notes on timing, tone, or approach — null if none>"
}}"""

_FALLBACK: dict = {
    "subject": "Review Required — Outreach Not Generated",
    "email_body": None,
    "follow_up_email": None,
    "linkedin_message": None,
    "call_notes": None,
    "chosen_channel": "deferred",
    "agent_reasoning": "Agent unavailable — defaulting to deferred.",
    "requires_human_review": True,
    "review_reason": "Agent unavailable — review before sending",
    "personalisation_notes": None,
    "fallback": True,
}


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


def _apply_deterministic_overrides(result: dict, lead: dict, analysis: dict) -> dict:
    """Enforce hard rules the LLM cannot override."""
    personal_domains = {"gmail.com", "hotmail.com", "yahoo.com", "outlook.com"}
    email = lead.get("email", "")
    domain = email.split("@")[-1].lower() if "@" in email else ""

    # Personal email domain → always deferred + human review
    if domain in personal_domains:
        result["chosen_channel"] = "deferred"
        result["requires_human_review"] = True
        result["review_reason"] = result.get("review_reason") or "Personal email domain"

    # Low score → always deferred + human review
    overall_score = analysis.get("overall_score") or 0
    if overall_score < 60:
        result["chosen_channel"] = "deferred"
        result["requires_human_review"] = True
        result["review_reason"] = result.get("review_reason") or f"Low overall score ({overall_score})"

    # Low confidence → human review (keep channel but flag)
    confidence = analysis.get("confidence_score") or 1.0
    if confidence < 0.6:
        result["requires_human_review"] = True
        result["review_reason"] = result.get("review_reason") or f"Low confidence score ({confidence:.2f})"

    # Missing linkedin_message → strip linkedin from chosen_channel
    if not result.get("linkedin_message"):
        if result.get("chosen_channel") == "linkedin":
            result["chosen_channel"] = "email"
        elif result.get("chosen_channel") == "both":
            result["chosen_channel"] = "email"

    return result


async def run_outreach_agent(lead: dict, analysis: dict) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    email = lead.get("email", "")
    email_domain = email.split("@")[-1] if email and "@" in email else "unknown"

    user_message = (
        f"Lead Information:\n"
        f"Name: {lead.get('first_name', 'Unknown')} {lead.get('last_name', 'Unknown')}\n"
        f"Email: {email} (domain: {email_domain})\n"
        f"Company: {lead.get('company') or 'Unknown'}\n"
        f"Job Title: {lead.get('job_title') or 'Unknown'}\n"
        f"Source: {lead.get('source') or 'Unknown'}\n"
        f"Notes: {lead.get('notes') or 'None'}\n\n"
        f"Analysis:\n"
        f"Persona Type: {analysis.get('persona_type') or 'Unknown'}\n"
        f"Overall Score: {analysis.get('overall_score', 0)}/100\n"
        f"Confidence Score: {analysis.get('confidence_score', 0)}\n"
        f"Pain Points: {analysis.get('pain_points') or 'Unknown'}\n"
        f"Buying Signals: {analysis.get('buying_signals') or 'None'}\n"
        f"Recommended Action: {analysis.get('recommended_action') or 'Unknown'}\n"
    )

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw_text = response.content[0].text
        result = json.loads(_extract_json(raw_text))
        result = _apply_deterministic_overrides(result, lead, analysis)
        return result
    except Exception as exc:
        _logger.warning("Outreach agent service failed: %s", exc)
        return {**_FALLBACK}
