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
)

_logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)

_ALLOWED_ACTIONS = {
    "analyze_lead",
    "generate_outreach",
    "sync_hubspot",
    "create_hubspot_task",
    "mark_needs_review",
    "skip_outreach",
}

_SYSTEM_PROMPT = f"""You are the GTM Orchestrator Agent for {COMPANY_NAME}, {COMPANY_LOCATION}.

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

Your job is to analyse incoming leads and decide which GTM actions to execute to move them through the pipeline toward a sales conversation with {COMPANY_NAME}.

Given a lead and optional analysis data, produce a JSON workflow plan specifying which actions to execute.

## Decision Rules
- If the lead email domain is personal (gmail.com, hotmail.com, yahoo.com, outlook.com): include mark_needs_review and do NOT include sync_hubspot
- If company or job_title is missing: include mark_needs_review
- If no analysis is provided: include analyze_lead as the first action
- If overall_score >= 75: include generate_outreach and sync_hubspot
- If overall_score >= 85: also include create_hubspot_task
- If confidence_score < 0.6: include mark_needs_review
- Never include both skip_outreach and generate_outreach

## Allowed Actions (use ONLY these — any other action will be rejected)
- analyze_lead
- generate_outreach
- sync_hubspot
- create_hubspot_task
- mark_needs_review
- skip_outreach

## Output Format
Return ONLY a valid JSON object with no explanation or markdown fences:
{{
  "actions": ["action_one", "action_two"],
  "requires_human_review": false,
  "reasoning_summary": "Brief explanation of why these actions were selected"
}}"""

_FALLBACK: dict = {
    "actions": ["mark_needs_review"],
    "requires_human_review": True,
    "reasoning_summary": "Agent planning failed — flagged for manual review",
}


def _extract_json(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


async def plan_workflow(lead, latest_analysis=None) -> dict:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    email_domain = (
        lead.email.split("@")[-1] if lead.email and "@" in lead.email else "unknown"
    )

    user_message = (
        f"Lead Information:\n"
        f"Name: {lead.first_name or 'Unknown'} {lead.last_name or 'Unknown'}\n"
        f"Email: {lead.email} (domain: {email_domain})\n"
        f"Company: {lead.company or 'MISSING'}\n"
        f"Job Title: {lead.job_title or 'MISSING'}\n"
        f"Website: {lead.company_website or 'Unknown'}\n"
        f"Source: {lead.source or 'Unknown'}\n"
        f"Status: {lead.status}\n"
    )

    if latest_analysis is not None:
        user_message += (
            f"\nAnalysis Available:\n"
            f"Overall Score: {latest_analysis.overall_score}\n"
            f"Confidence Score: {latest_analysis.confidence_score}\n"
            f"Persona: {latest_analysis.persona_type}\n"
            f"Recommended Action: {getattr(latest_analysis, 'recommended_action', 'N/A')}\n"
        )
    else:
        user_message += "\nNo analysis available yet.\n"

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw_text = response.content[0].text
        plan = json.loads(_extract_json(raw_text))
        plan["actions"] = [a for a in plan.get("actions", []) if a in _ALLOWED_ACTIONS]
        return plan
    except Exception as exc:
        _logger.warning("GTM workflow agent failed: %s", exc)
        return {**_FALLBACK}
