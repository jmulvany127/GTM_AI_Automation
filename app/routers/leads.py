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
