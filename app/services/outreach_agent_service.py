import json
import logging
import re
from anthropic import AsyncAnthropic
from app.config import get_settings

_logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_SYSTEM_PROMPT = """You are a specialised B2B outreach execution agent for a Go-To-Market automation platform.

Your responsibility is the FULL outreach motion for each lead: you generate all outreach content AND make the channel execution decision in a single pass.

## Content You Must Generate

- **subject** — a personalised email subject line
- **email_body** — a personalised, ready-to-send email under 130 words
- **follow_up_email** — a follow-up email under 90 words, sent if no reply after 5 days
- **linkedin_message** — a LinkedIn connection/message under 300 characters. This message will be sent MANUALLY by a human sales rep — it must be complete, professional, and ready to copy-paste without edits.
- **call_notes** — brief call preparation notes covering key talking points and objections

## Execution Decision You Must Make

After generating content, decide:

- **chosen_channel** — one of: "email", "linkedin", "both", or "deferred"
- **agent_reasoning** — 2–3 sentences explaining your channel and review decision
- **requires_human_review** — boolean
- **review_reason** — brief explanation if requires_human_review is true, otherwise null
- **personalisation_notes** — optional timing, tone, or approach notes; null if none

## Decision Guidance (these are enforced in code — use them as signals, not hard constraints)

### Channel Selection
- overall_score >= 80 → prefer "both" (email + LinkedIn)
- overall_score 60–79 → prefer "email"
- overall_score < 60 → "deferred" and set requires_human_review=true
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
  "subject": "<email subject>",
  "email_body": "<personalised email body under 130 words>",
  "follow_up_email": "<follow-up email under 90 words>",
  "linkedin_message": "<LinkedIn message under 300 characters>",
  "call_notes": "<brief call preparation notes>",
  "chosen_channel": "<email|linkedin|both|deferred>",
  "agent_reasoning": "<2-3 sentences>",
  "requires_human_review": false,
  "review_reason": "<null or brief reason>",
  "personalisation_notes": "<null or notes>"
}"""

_FALLBACK: dict = {
    "subject": None,
    "email_body": None,
    "follow_up_email": None,
    "linkedin_message": None,
    "call_notes": None,
    "chosen_channel": "deferred",
    "agent_reasoning": "Agent unavailable — review before sending.",
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
        f"Source: {lead.get('source') or 'Unknown'}\n\n"
        f"Analysis:\n"
        f"Persona Type: {analysis.get('persona_type') or 'Unknown'}\n"
        f"Overall Score: {analysis.get('overall_score', 0)}/100\n"
        f"Confidence Score: {analysis.get('confidence_score', 0)}\n"
        f"Pain Points: {analysis.get('pain_points') or 'Unknown'}\n"
        f"Buying Signals: {analysis.get('buying_signals') or 'None'}\n"
        f"Recommended Action: {analysis.get('recommended_action') or 'Unknown'}\n\n"
        f"Generate all outreach content for this lead and make the channel execution decision."
    )

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
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
