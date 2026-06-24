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
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from app.services.outreach_agent_service import run_outreach_agent
from app.services import gmail_service, slack_service

_logger = logging.getLogger(__name__)

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

    # Fetch most recent outreach message
    outreach_result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.lead_id == lead_id)
        .order_by(OutreachMessage.created_at.desc())
        .limit(1)
    )
    outreach = outreach_result.scalar_one_or_none()
    if outreach is None:
        raise HTTPException(status_code=404, detail="No outreach message found for this lead")

    # Build dicts from ORM objects
    lead_dict = {
        k: getattr(lead, k)
        for k in ["id", "first_name", "last_name", "email", "company", "job_title", "source", "status", "company_website"]
    }
    analysis_dict = {
        k: getattr(analysis, k)
        for k in ["id", "persona_type", "pain_points", "buying_signals", "overall_score", "confidence_score", "recommended_action"]
    }
    outreach_dict = {
        k: getattr(outreach, k)
        for k in ["id", "subject", "email_body", "linkedin_message", "follow_up_email"]
    }

    # Call the outreach agent
    agent_result = await run_outreach_agent(lead_dict, analysis_dict, outreach_dict)

    # Save OutreachExecutionLog
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

    # Update lead status if human review required
    if log.requires_human_review:
        lead.status = "needs_review"
        await db.commit()

    # --- Sending and alerting ---
    # DIAGNOSTIC LOG OUTPUT (lead 25, 2026-06-24) — captured before Task 2 fixes:
    # [DEBUG] outreach decision — chosen_channel='both' requires_human_review=False overall_score=70
    # [DEBUG] path=sending — chosen_channel='both'
    # [DEBUG] attempting Gmail send to 'alice.chen@salesforce-corp.net'
    # [DEBUG] gmail_service: GMAIL_SENDER_ADDRESS present=True len=22  GMAIL_APP_PASSWORD present=True
    # [DEBUG] Gmail send result — sent=True new_status='sent'
    # [DEBUG] LinkedIn sending not yet automated for lead 25 — manual action required
    # [DEBUG] Slack threshold check — overall_score=70 >= 70: True
    # [DEBUG] slack_service: SLACK_WEBHOOK_URL present=True len=81
    # ROOT CAUSE DIAGNOSIS:
    # 1. docker-compose.yml uses `${VAR:-}` (default-to-empty-string) in the environment block.
    #    Docker Compose resolves this from the .env file during compose interpolation, so on the
    #    developer machine the vars are present. However if the host shell does NOT export these
    #    vars (e.g. CI, fresh checkout, or running compose without the .env in scope), the
    #    `environment` block overrides the `env_file` values with empty strings because
    #    `environment` takes precedence over `env_file` in Docker Compose. This is a latent bug.
    # 2. gmail_service.send_email silently returns False with no logging when env vars are
    #    missing — making the failure completely invisible in Docker logs.
    # 3. slack_service.send_alert silently returns False with no logging when SLACK_WEBHOOK_URL
    #    is missing — same invisible failure pattern.
    chosen_channel = log.chosen_channel or ""
    overall_score = analysis_dict.get("overall_score") or 0

    _logger.warning(
        "[DEBUG] outreach decision — chosen_channel=%r requires_human_review=%r overall_score=%r",
        chosen_channel,
        log.requires_human_review,
        overall_score,
    )

    if log.requires_human_review:
        _logger.warning("[DEBUG] path=human_review → sending Slack review alert")
        review_alert = slack_service.build_review_alert(
            first_name=lead_dict["first_name"],
            last_name=lead_dict["last_name"],
            company=lead_dict.get("company") or "",
            overall_score=overall_score,
            review_reason=log.review_reason,
            lead_id=lead_id,
        )
        await slack_service.send_alert(review_alert)
    else:
        _logger.warning("[DEBUG] path=sending — chosen_channel=%r", chosen_channel)
        new_status = "pending"

        if chosen_channel in ("email", "both"):
            _logger.warning("[DEBUG] attempting Gmail send to %r", lead_dict["email"])
            sent = await asyncio.to_thread(
                gmail_service.send_email,
                lead_dict["email"],
                outreach_dict.get("subject") or "",
                outreach_dict.get("email_body") or "",
            )
            new_status = "sent" if sent else "failed"
            _logger.warning("[DEBUG] Gmail send result — sent=%r new_status=%r", sent, new_status)

        if chosen_channel in ("linkedin", "both"):
            _logger.warning(
                "[DEBUG] LinkedIn sending not yet automated for lead %s — manual action required",
                lead_id,
            )
            if new_status == "pending":
                new_status = "linkedin_pending"

        log.execution_status = new_status
        await db.commit()

        # Slack alert for high-scoring leads (threshold 70 = 7.0/10)
        _logger.warning("[DEBUG] Slack threshold check — overall_score=%r >= 70: %r", overall_score, overall_score >= 70)
        if overall_score >= 70:
            lead_alert = slack_service.build_lead_alert(
                first_name=lead_dict["first_name"],
                last_name=lead_dict["last_name"],
                company=lead_dict.get("company") or "",
                overall_score=overall_score,
                chosen_channel=chosen_channel,
                recommended_action=analysis_dict.get("recommended_action") or "",
                lead_id=lead_id,
            )
            await slack_service.send_alert(lead_alert)

    return {
        "id": log.id,
        "lead_id": log.lead_id,
        "outreach_message_id": log.outreach_message_id,
        "chosen_channel": log.chosen_channel,
        "agent_reasoning": log.agent_reasoning,
        "requires_human_review": log.requires_human_review,
        "review_reason": log.review_reason,
        "execution_status": log.execution_status,
        "created_at": log.created_at,
    }
