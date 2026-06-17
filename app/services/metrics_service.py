from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import LeadAnalysis
from app.models.crm_log import CrmSyncLog
from app.models.metrics import AutomationMetrics


async def get_roi_metrics(db: AsyncSession) -> dict:
    result = await db.execute(select(func.count()).select_from(AutomationMetrics))
    total_leads_processed: int = result.scalar_one_or_none() or 0

    result = await db.execute(
        select(func.count()).select_from(LeadAnalysis).where(LeadAnalysis.overall_score >= 75)
    )
    high_priority_leads: int = result.scalar_one_or_none() or 0

    result = await db.execute(select(func.sum(AutomationMetrics.estimated_time_saved_minutes)))
    minutes_sum: float = result.scalar_one_or_none() or 0.0
    estimated_hours_saved: float = minutes_sum / 60.0

    result = await db.execute(select(func.avg(AutomationMetrics.automated_time_seconds)))
    average_processing_time_seconds: float = result.scalar_one_or_none() or 0.0

    result = await db.execute(select(func.avg(LeadAnalysis.overall_score)))
    average_lead_score: float = result.scalar_one_or_none() or 0.0

    result = await db.execute(
        select(func.count()).select_from(CrmSyncLog).where(CrmSyncLog.sync_status == "success")
    )
    success_count: int = result.scalar_one_or_none() or 0

    result = await db.execute(select(func.count()).select_from(CrmSyncLog))
    total_crm: int = result.scalar_one_or_none() or 0

    hubspot_sync_success_rate: float = (success_count / total_crm) if total_crm > 0 else 0.0

    return {
        "total_leads_processed": total_leads_processed,
        "high_priority_leads": high_priority_leads,
        "estimated_hours_saved": float(estimated_hours_saved),
        "average_processing_time_seconds": float(average_processing_time_seconds),
        "average_lead_score": float(average_lead_score),
        "hubspot_sync_success_rate": hubspot_sync_success_rate,
    }
