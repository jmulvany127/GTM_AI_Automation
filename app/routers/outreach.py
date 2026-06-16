from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis
from app.models.outreach import OutreachMessage
from app.schemas.outreach import OutreachCreate, OutreachRead
from app.services import outreach_service

router = APIRouter(prefix="/leads", tags=["outreach"])


@router.post("/{lead_id}/generate-outreach", response_model=OutreachRead, status_code=status.HTTP_200_OK)
async def generate_outreach_endpoint(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    analysis_result = await db.execute(
        select(LeadAnalysis)
        .where(LeadAnalysis.lead_id == lead_id)
        .order_by(LeadAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="No analysis found for this lead — run /analyze first")

    outreach_dict = await outreach_service.generate_outreach(lead, analysis)
    create_data = OutreachCreate(**outreach_dict).model_dump()
    outreach = OutreachMessage(**create_data, lead_id=lead_id)
    db.add(outreach)
    await db.commit()
    await db.refresh(outreach)
    return outreach
