import time
import httpx

_BASE = "https://api.hubapi.com"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code >= 300:
        raise RuntimeError(
            f"HubSpot API error {response.status_code}: {response.text}"
        )


async def search_contact_by_email(token: str, email: str) -> str | None:
    payload = {
        "filterGroups": [
            {"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}
        ],
        "properties": ["email"],
        "limit": 1,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_BASE}/crm/v3/objects/contacts/search",
            headers=_headers(token),
            json=payload,
        )
    if response.status_code == 404:
        return None
    _raise_for_status(response)
    results = response.json().get("results", [])
    return results[0]["id"] if results else None


async def create_or_update_contact(token: str, lead, analysis) -> str:
    properties = {
        "firstname": lead.first_name,
        "lastname": lead.last_name,
        "email": lead.email,
        "company": lead.company,
        "jobtitle": lead.job_title,
        "website": lead.company_website,
        "hs_lead_status": lead.status,
        "ai_fit_score": str(analysis.fit_score) if analysis.fit_score is not None else "",
        "ai_overall_score": str(analysis.overall_score) if analysis.overall_score is not None else "",
        "ai_recommended_action": analysis.recommended_action or "",
    }
    existing_id = await search_contact_by_email(token, lead.email)

    async with httpx.AsyncClient() as client:
        if existing_id:
            response = await client.patch(
                f"{_BASE}/crm/v3/objects/contacts/{existing_id}",
                headers=_headers(token),
                json={"properties": properties},
            )
        else:
            response = await client.post(
                f"{_BASE}/crm/v3/objects/contacts",
                headers=_headers(token),
                json={"properties": properties},
            )
    _raise_for_status(response)
    return response.json()["id"]


async def create_note(token: str, contact_id: str, analysis, outreach) -> str:
    lines = [
        f"Persona: {analysis.persona_type or 'N/A'}",
        f"Pain Points: {analysis.pain_points or 'N/A'}",
        f"Buying Signals: {analysis.buying_signals or 'N/A'}",
        f"Overall Score: {analysis.overall_score}",
        f"Recommended Action: {analysis.recommended_action or 'N/A'}",
    ]
    if outreach:
        lines += [
            f"Email Subject: {outreach.subject or 'N/A'}",
            f"Email Body: {outreach.email_body or 'N/A'}",
        ]
    body = "\n".join(lines)

    payload = {
        "properties": {"hs_note_body": body},
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
            }
        ],
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_BASE}/crm/v3/objects/notes",
            headers=_headers(token),
            json=payload,
        )
    _raise_for_status(response)
    return response.json()["id"]


async def create_task(token: str, contact_id: str, recommended_action: str) -> str:
    due_ms = int((time.time() + 3 * 86400) * 1000)
    payload = {
        "properties": {
            "hs_task_subject": recommended_action,
            "hs_task_status": "NOT_STARTED",
            "hs_task_type": "TODO",
            "hs_timestamp": str(due_ms),
        },
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 204}],
            }
        ],
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_BASE}/crm/v3/objects/tasks",
            headers=_headers(token),
            json=payload,
        )
    _raise_for_status(response)
    return response.json()["id"]
