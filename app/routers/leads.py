import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis
from app.models.outreach import OutreachMessage
from app.models.outreach_execution_log import OutreachExecutionLog
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from app.routers.workflow import execute_run_outreach_agent

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])


class ParseRequest(BaseModel):
    raw_text: str = Field(..., min_length=10)


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


@router.post("/parse")
async def parse_lead(payload: ParseRequest):
    from app.services.lead_parse_service import parse_lead_from_text
    result = await parse_lead_from_text(payload.raw_text)
    if "parse_error" in result:
        raise HTTPException(status_code=422, detail=result["parse_error"])
    if not result.get("email"):
        raise HTTPException(
            status_code=422,
            detail="Could not extract an email address from the provided text. Email is required to create a lead.",
        )
    return result


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

    log, _ = await execute_run_outreach_agent(lead, analysis, outreach, db)
    await db.commit()
    await db.refresh(log)

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
