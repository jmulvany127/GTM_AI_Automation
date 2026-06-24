import logging
import os

import httpx

_logger = logging.getLogger(__name__)


async def send_linkedin_action_required(lead: dict, linkedin_message: str, lead_url: str) -> bool:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        _logger.error(
            "slack_service: cannot send LinkedIn alert — SLACK_WEBHOOK_URL is not set"
        )
        return False

    first_name = lead.get("first_name", "")
    last_name = lead.get("last_name", "")
    company = lead.get("company", "")
    title = lead.get("job_title") or lead.get("title", "")
    score = lead.get("overall_score", "N/A")
    if isinstance(score, (int, float)) and score > 10:
        score = round(score / 10, 1)

    message = (
        f"\U0001f4e8 Manual LinkedIn Action Required\n"
        f"Lead: {first_name} {last_name} — {company}\n"
        f"Title: {title}\n"
        f"Score: {score}/10\n\n"
        f"Message to send:\n"
        f'"{linkedin_message}"\n\n'
        f"View lead: {lead_url}"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json={"text": message})
        response.raise_for_status()
        return True
    except Exception as exc:
        _logger.error("LinkedIn action required Slack alert failed: %s", exc)
        return False


async def send_alert(message: str) -> bool:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        _logger.error(
            "slack_service: cannot send — SLACK_WEBHOOK_URL is not set; "
            "check env vars are set in .env and not overridden with empty values"
        )
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json={"text": message})
        response.raise_for_status()
        return True
    except Exception as exc:
        _logger.error("Slack alert failed: %s", exc)
        return False


def build_lead_alert(
    first_name: str,
    last_name: str,
    company: str,
    overall_score: float,
    chosen_channel: str,
    recommended_action: str,
    lead_id: int,
) -> str:
    display_score = overall_score / 10 if overall_score > 10 else overall_score
    return (
        f"\U0001f525 GTM Agent Alert\n"
        f"Lead: {first_name} {last_name} — {company}\n"
        f"Score: {display_score:.1f}/10\n"
        f"Channel Decision: {chosen_channel}\n"
        f"Recommended Action: {recommended_action}\n"
        f"View: http://localhost:8000/dashboard/leads/{lead_id}"
    )


def build_review_alert(
    first_name: str,
    last_name: str,
    company: str,
    overall_score: float,
    review_reason: str | None,
    lead_id: int,
) -> str:
    display_score = overall_score / 10 if overall_score > 10 else overall_score
    reason = review_reason or "No reason provided"
    return (
        f"⚠️ GTM Human Review Required\n"
        f"Lead: {first_name} {last_name} — {company}\n"
        f"Score: {display_score:.1f}/10\n"
        f"Review Reason: {reason}\n"
        f"View: http://localhost:8000/dashboard/leads/{lead_id}"
    )
