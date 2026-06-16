from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis
from app.schemas.analysis import LeadAnalysisCreate, LeadAnalysisRead
from app.services import ai_service

router = APIRouter(prefix="/leads", tags=["analysis"])


@router.post("/{lead_id}/analyze", response_model=LeadAnalysisRead, status_code=status.HTTP_200_OK)
async def analyze_lead_endpoint(lead_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    analysis_dict = await ai_service.analyze_lead(lead)
    create_data = LeadAnalysisCreate(**analysis_dict).model_dump()
    analysis = LeadAnalysis(**create_data, lead_id=lead_id)
    db.add(analysis)
    lead.status = "analyzed"
    await db.commit()
    await db.refresh(analysis)
    return analysis
