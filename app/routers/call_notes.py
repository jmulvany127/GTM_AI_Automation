import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.lead import Lead
from app.models.crm_log import CrmSyncLog
from app.models.call_analysis import CallAnalysis
from app.schemas.call_analysis import CallAnalysisRequest, CallAnalysisResponse
from app.services import call_intelligence_service, hubspot_service
from app.config import get_settings

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/call-notes", tags=["call-intelligence"])


@router.post("/analyze", response_model=CallAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_call(body: CallAnalysisRequest, db: AsyncSession = Depends(get_db)):
    if body.lead_id is not None:
        result = await db.execute(select(Lead).where(Lead.id == body.lead_id))
        lead = result.scalar_one_or_none()
        if lead is None:
            raise HTTPException(status_code=404, detail=f"Lead {body.lead_id} not found")

    analysis_dict = await call_intelligence_service.analyze_transcript(body.transcript)

    record = CallAnalysis(
        lead_id=body.lead_id,
        transcript=body.transcript,
        pain_points=analysis_dict.get("pain_points"),
        objections=analysis_dict.get("objections"),
        competitors=analysis_dict.get("competitors"),
        budget_signals=analysis_dict.get("budget_signals"),
        decision_timeline=analysis_dict.get("decision_timeline"),
        buying_intent_score=analysis_dict.get("buying_intent_score"),
        recommended_follow_up=analysis_dict.get("recommended_follow_up"),
        crm_note=analysis_dict.get("crm_note"),
        follow_up_email=analysis_dict.get("follow_up_email"),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    if body.lead_id is not None and record.crm_note:
        crm_result = await db.execute(
            select(CrmSyncLog)
            .where(CrmSyncLog.lead_id == body.lead_id)
            .where(CrmSyncLog.sync_status == "success")
            .order_by(CrmSyncLog.id.desc())
            .limit(1)
        )
        crm_log = crm_result.scalar_one_or_none()
        if crm_log and crm_log.external_contact_id:
            settings = get_settings()
            try:
                note_id = await hubspot_service.create_call_note(
                    settings.HUBSPOT_ACCESS_TOKEN,
                    crm_log.external_contact_id,
                    record.crm_note,
                )
                _logger.info("HubSpot call note created: %s for lead %d", note_id, body.lead_id)
            except Exception as exc:
                _logger.warning("Failed to create HubSpot note for lead %d: %s", body.lead_id, exc)

    return record
