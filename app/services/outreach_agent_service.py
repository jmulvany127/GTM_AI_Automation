import json
import logging
import re
from anthropic import AsyncAnthropic
from app.config import get_settings

_logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_SYSTEM_PROMPT = """You are a B2B outreach channel and timing decision agent for a Go-To-Market automation platform.

Your role is ONLY to decide which communication channel(s) to use for a lead and whether human review is needed.
You do NOT write outreach content — content has already been generated. You decide the execution strategy.

## Decision Signals

### Channel Selection (chosen_channel)
- overall_score >= 80 → prefer "both" (email + LinkedIn)
- overall_score 60–79 → prefer "email"
- overall_score < 60 → "deferred" and set requires_human_review=true
- If linkedin_message is empty, null, or missing in the outreach data → exclude LinkedIn; never choose "both" or "linkedin"
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
{
  "chosen_channel": "<email|linkedin|both|deferred>",
  "agent_reasoning": "<brief explanation of why this channel and review status was chosen>",
  "requires_human_review": false,
  "review_reason": "<null if no review needed, or brief reason>",
  "personalisation_notes": "<optional notes on timing, tone, or approach — null if none>"
}"""

_FALLBACK: dict = {
    "chosen_channel": "email",
    "agent_reasoning": "Agent decision unavailable — defaulting to email.",
    "requires_human_review": True,
    "review_reason": "Agent decision unavailable",
    "personalisation_notes": None,
    "fallback": True,
}


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


def _apply_deterministic_overrides(result: dict, lead: dict, analysis: dict, outreach: dict) -> dict:
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
    if not outreach.get("linkedin_message"):
        if result.get("chosen_channel") == "linkedin":
            result["chosen_channel"] = "email"
        elif result.get("chosen_channel") == "both":
            result["chosen_channel"] = "email"

    return result


async def run_outreach_agent(lead: dict, analysis: dict, outreach: dict) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    email = lead.get("email", "")
    email_domain = email.split("@")[-1] if email and "@" in email else "unknown"
    linkedin_message = outreach.get("linkedin_message") or ""

    user_message = (
        f"Lead Information:\n"
        f"Name: {lead.get('first_name', 'Unknown')} {lead.get('last_name', 'Unknown')}\n"
        f"Email: {email} (domain: {email_domain})\n"
        f"Company: {lead.get('company') or 'Unknown'}\n"
        f"Job Title: {lead.get('job_title') or 'Unknown'}\n"
        f"Source: {lead.get('source') or 'Unknown'}\n\n"
        f"Analysis:\n"
        f"Persona Type: {analysis.get('persona_type') or 'Unknown'}\n"
        f"Overall Score: {analysis.get('overall_score', 0)}/100\n"
        f"Confidence Score: {analysis.get('confidence_score', 0)}\n"
        f"Pain Points: {analysis.get('pain_points') or 'Unknown'}\n"
        f"Buying Signals: {analysis.get('buying_signals') or 'None'}\n"
        f"Recommended Action: {analysis.get('recommended_action') or 'Unknown'}\n\n"
        f"Outreach Content Available:\n"
        f"Email Subject: {outreach.get('subject') or 'Not generated'}\n"
        f"Email Body: {'Yes' if outreach.get('email_body') else 'No'}\n"
        f"Follow-up Email: {'Yes' if outreach.get('follow_up_email') else 'No'}\n"
        f"LinkedIn Message: {'Yes — ' + linkedin_message if linkedin_message else 'No — LinkedIn message is missing or empty'}\n"
        f"Call Notes: {'Yes' if outreach.get('call_notes') else 'No'}\n"
    )

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw_text = response.content[0].text
        result = json.loads(_extract_json(raw_text))
        result = _apply_deterministic_overrides(result, lead, analysis, outreach)
        return result
    except Exception as exc:
        _logger.warning("Outreach agent service failed: %s", exc)
        return {**_FALLBACK}
