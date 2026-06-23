import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis
from app.models.outreach import OutreachMessage
from app.models.outreach_execution_log import OutreachExecutionLog
from app.models.crm_log import CrmSyncLog
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from app.services.outreach_agent_service import run_outreach_agent
from app.services import gmail_service, slack_service, hubspot_service
from app.config import get_settings

_logger = logging.getLogger(__name__)


def _build_outreach_note(agent_result: dict, log) -> str:
    channel = agent_result.get("chosen_channel") or "unknown"
    exec_status = log.execution_status or "unknown"
    linkedin_part = " LinkedIn message pending manual send." if channel in ("linkedin", "both") else ""
    return f"Outreach agent executed. Channel: {channel}. Email status: {exec_status}.{linkedin_part}".strip()


router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    db.add(lead)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    await db.refresh(lead)
    return lead


@router.get("", response_model=list[LeadRead])
async def list_leads(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead))
    return result.scalars().all()


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: int, payload: LeadUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete lead with associated records")


@router.post("/{lead_id}/run-outreach-agent", status_code=status.HTTP_200_OK)
async def run_outreach_agent_endpoint(lead_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch lead
    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    existing_log = await db.execute(
        select(OutreachExecutionLog).where(OutreachExecutionLog.lead_id == lead_id).limit(1)
    )
    if existing_log.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=400,
            detail="Outreach agent has already been run on this lead.",
        )

    # Fetch most recent analysis
    analysis_result = await db.execute(
        select(LeadAnalysis)
        .where(LeadAnalysis.lead_id == lead_id)
        .order_by(LeadAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="No analysis found for this lead")

    # Build dicts from ORM objects
    lead_dict = {
        k: getattr(lead, k)
        for k in ["id", "first_name", "last_name", "email", "company", "job_title", "source", "status", "company_website"]
    }
    analysis_dict = {
        k: getattr(analysis, k)
        for k in ["id", "persona_type", "pain_points", "buying_signals", "overall_score", "confidence_score", "recommended_action"]
    }

    # Call the outreach agent (generates content + makes channel decision in one pass)
    agent_result = await run_outreach_agent(lead_dict, analysis_dict)

    # Step 1 — Write OutreachMessage
    outreach = OutreachMessage(
        lead_id=lead_id,
        subject=agent_result.get("subject"),
        email_body=agent_result.get("email_body"),
        follow_up_email=agent_result.get("follow_up_email"),
        linkedin_message=agent_result.get("linkedin_message"),
        call_notes=agent_result.get("call_notes"),
    )
    db.add(outreach)
    await db.commit()
    await db.refresh(outreach)

    # Step 2 — Write OutreachExecutionLog
    log = OutreachExecutionLog(
        lead_id=lead_id,
        outreach_message_id=outreach.id,
        chosen_channel=agent_result.get("chosen_channel"),
        agent_reasoning=agent_result.get("agent_reasoning"),
        requires_human_review=agent_result.get("requires_human_review", False),
        review_reason=agent_result.get("review_reason"),
        execution_status="pending",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    # Step 3 — Update lead status if human review required
    if log.requires_human_review:
        lead.status = "needs_review"
        await db.commit()

    # Step 4 — Gmail / LinkedIn execution
    chosen_channel = log.chosen_channel or ""
    new_status = "pending"

    if not log.requires_human_review:
        if chosen_channel in ("email", "both"):
            sent = await asyncio.to_thread(
                gmail_service.send_email,
                lead_dict["email"],
                agent_result.get("subject") or "",
                agent_result.get("email_body") or "",
            )
            new_status = "sent" if sent else "failed"

        if chosen_channel in ("linkedin", "both"):
            new_status = "pending_manual"

        log.execution_status = new_status
        await db.commit()

    # Step 5 — Slack alert
    overall_score = analysis_dict.get("overall_score") or 0
    if log.requires_human_review:
        await slack_service.send_alert(
            slack_service.build_review_alert(
                first_name=lead_dict["first_name"],
                last_name=lead_dict["last_name"],
                company=lead_dict.get("company") or "",
                overall_score=overall_score,
                review_reason=log.review_reason,
                lead_id=lead_id,
            )
        )
    elif overall_score >= 70:
        await slack_service.send_alert(
            slack_service.build_lead_alert(
                first_name=lead_dict["first_name"],
                last_name=lead_dict["last_name"],
                company=lead_dict.get("company") or "",
                overall_score=overall_score,
                chosen_channel=chosen_channel,
                recommended_action=analysis_dict.get("recommended_action") or "",
                lead_id=lead_id,
            )
        )

    # Step 6 — HubSpot note (if lead has been synced to HubSpot)
    crm_result = await db.execute(
        select(CrmSyncLog)
        .where(CrmSyncLog.lead_id == lead_id, CrmSyncLog.sync_status == "success")
        .order_by(CrmSyncLog.created_at.desc())
        .limit(1)
    )
    crm_sync = crm_result.scalar_one_or_none()
    if crm_sync and crm_sync.external_contact_id:
        token = get_settings().HUBSPOT_ACCESS_TOKEN
        try:
            note_body = _build_outreach_note(agent_result, log)
            await hubspot_service.create_call_note(token, crm_sync.external_contact_id, note_body)
        except Exception as exc:
            _logger.warning("HubSpot outreach note failed for lead %s: %s", lead_id, exc)

    return {
        "id": log.id,
        "lead_id": log.lead_id,
        "outreach_message_id": log.outreach_message_id,
        "subject": outreach.subject,
        "email_body": outreach.email_body,
        "follow_up_email": outreach.follow_up_email,
        "linkedin_message": outreach.linkedin_message,
        "call_notes": outreach.call_notes,
        "chosen_channel": log.chosen_channel,
        "agent_reasoning": log.agent_reasoning,
        "requires_human_review": log.requires_human_review,
        "review_reason": log.review_reason,
        "execution_status": log.execution_status,
        "created_at": log.created_at,
    }
