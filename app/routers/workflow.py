import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis
from app.models.outreach import OutreachMessage
from app.models.metrics import AutomationMetrics
from app.schemas.analysis import LeadAnalysisCreate
from app.schemas.outreach import OutreachCreate
from app.services import ai_service, outreach_service
from app.agents import gtm_workflow_agent

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["workflow"])

_ALLOWED_ACTIONS = {
    "analyze_lead",
    "generate_outreach",
    "sync_hubspot",
    "create_hubspot_task",
    "mark_needs_review",
    "skip_outreach",
}


async def execute_analyze_lead(lead, db: AsyncSession) -> dict:
    analysis_dict = await ai_service.analyze_lead(lead)
    create_data = LeadAnalysisCreate(**analysis_dict).model_dump()
    analysis = LeadAnalysis(**create_data, lead_id=lead.id)
    db.add(analysis)
    lead.status = "analyzed"
    await db.flush()
    return analysis_dict


async def execute_generate_outreach(lead, db: AsyncSession) -> dict:
    analysis_result = await db.execute(
        select(LeadAnalysis)
        .where(LeadAnalysis.lead_id == lead.id)
        .order_by(LeadAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()
    outreach_dict = await outreach_service.generate_outreach(lead, analysis)
    create_data = OutreachCreate(**outreach_dict).model_dump()
    outreach = OutreachMessage(**create_data, lead_id=lead.id)
    db.add(outreach)
    await db.flush()
    return outreach_dict


async def execute_sync_hubspot(lead, db: AsyncSession) -> dict:
    _logger.info("hubspot sync skipped, not yet implemented")
    return {"status": "skipped"}


async def execute_create_hubspot_task(lead, db: AsyncSession) -> dict:
    _logger.info("create hubspot task skipped, not yet implemented")
    return {"status": "skipped"}


async def execute_mark_needs_review(lead, db: AsyncSession) -> dict:
    lead.status = "needs_review"
    return {"status": "flagged"}


async def execute_skip_outreach(lead, db: AsyncSession) -> dict:
    lead.status = "skipped"
    return {"status": "skipped"}


_DISPATCH = {
    "analyze_lead": execute_analyze_lead,
    "generate_outreach": execute_generate_outreach,
    "sync_hubspot": execute_sync_hubspot,
    "create_hubspot_task": execute_create_hubspot_task,
    "mark_needs_review": execute_mark_needs_review,
    "skip_outreach": execute_skip_outreach,
}


@router.post("/{lead_id}/run-agent", status_code=status.HTTP_200_OK)
async def run_agent_endpoint(lead_id: int, db: AsyncSession = Depends(get_db)):
    start_time = time.time()

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
    latest_analysis = analysis_result.scalar_one_or_none()

    plan = await gtm_workflow_agent.plan_workflow(lead, latest_analysis)

    actions_executed = []
    results = {}
    for action in plan.get("actions", []):
        if action not in _ALLOWED_ACTIONS:
            continue
        executor = _DISPATCH[action]
        result = await executor(lead, db)
        actions_executed.append(action)
        results[action] = result

    automated_time_seconds = time.time() - start_time
    manual_time_estimate_minutes = 25
    estimated_time_saved_minutes = manual_time_estimate_minutes - (automated_time_seconds / 60)

    metrics = AutomationMetrics(
        lead_id=lead_id,
        workflow_name="gtm_workflow",
        actions_executed=json.dumps(actions_executed),
        requires_human_review=plan.get("requires_human_review", False),
        reasoning_summary=plan.get("reasoning_summary"),
        manual_time_estimate_minutes=manual_time_estimate_minutes,
        automated_time_seconds=automated_time_seconds,
        estimated_time_saved_minutes=estimated_time_saved_minutes,
    )
    db.add(metrics)
    await db.commit()

    return {
        "lead_id": lead_id,
        "plan": plan,
        "actions_executed": actions_executed,
        "results": results,
        "metrics": {
            "automated_time_seconds": automated_time_seconds,
            "estimated_time_saved_minutes": estimated_time_saved_minutes,
            "manual_time_estimate_minutes": manual_time_estimate_minutes,
        },
    }
