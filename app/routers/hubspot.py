from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.analysis import LeadAnalysis
from app.models.crm_log import CrmSyncLog
from app.models.lead import Lead
from app.models.outreach import OutreachMessage
from app.schemas.crm_log import CrmSyncLogRead
from app.services import hubspot_service

router = APIRouter(prefix="/leads", tags=["hubspot"])


@router.post("/{lead_id}/sync-hubspot", response_model=CrmSyncLogRead)
async def sync_hubspot(lead_id: int, db: AsyncSession = Depends(get_db)):
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
        raise HTTPException(status_code=404, detail="No analysis found for this lead")

    outreach_result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.lead_id == lead_id)
        .order_by(OutreachMessage.created_at.desc())
        .limit(1)
    )
    outreach = outreach_result.scalar_one_or_none()

    token = get_settings().HUBSPOT_ACCESS_TOKEN

    try:
        contact_id = await hubspot_service.create_or_update_contact(token, lead, analysis)
        await hubspot_service.create_note(token, contact_id, analysis, outreach)
        if analysis.overall_score is not None and analysis.overall_score >= 85:
            await hubspot_service.create_task(token, contact_id, analysis.recommended_action or "")

        log = CrmSyncLog(
            lead_id=lead_id,
            sync_status="success",
            external_contact_id=contact_id,
        )
    except Exception as exc:
        log = CrmSyncLog(
            lead_id=lead_id,
            sync_status="failed",
            error_message=str(exc),
        )

    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
