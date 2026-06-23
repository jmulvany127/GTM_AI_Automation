import asyncio
import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.lead import Lead
from app.models.analysis import LeadAnalysis
from app.models.crm_log import CrmSyncLog
from app.models.outreach import OutreachMessage
from app.models.metrics import AutomationMetrics
from app.models.outreach_execution_log import OutreachExecutionLog
from app.schemas.analysis import LeadAnalysisCreate
from app.services import ai_service, hubspot_service, gmail_service, slack_service
from app.services.outreach_agent_service import run_outreach_agent
from app.config import get_settings
from app.agents import gtm_workflow_agent
from app.agents.gtm_workflow_agent import _ALLOWED_ACTIONS

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["workflow"])


async def execute_analyze_lead(lead, db: AsyncSession) -> dict:
    analysis_dict = await ai_service.analyze_lead(lead)
    create_data = LeadAnalysisCreate(**analysis_dict).model_dump()
    analysis = LeadAnalysis(**create_data, lead_id=lead.id)
    db.add(analysis)
    lead.status = "analyzed"
    await db.flush()
    return analysis_dict


async def execute_run_outreach_agent(lead, db: AsyncSession) -> dict:
    analysis_result = await db.execute(
        select(LeadAnalysis)
        .where(LeadAnalysis.lead_id == lead.id)
        .order_by(LeadAnalysis.created_at.desc())
        .limit(1)
    )
    analysis_obj = analysis_result.scalar_one_or_none()

    lead_dict = {
        k: getattr(lead, k)
        for k in ["id", "first_name", "last_name", "email", "company", "job_title", "source", "status", "company_website"]
    }
    analysis_dict = (
        {
            k: getattr(analysis_obj, k)
            for k in ["id", "persona_type", "pain_points", "buying_signals", "overall_score", "confidence_score", "recommended_action"]
        }
        if analysis_obj
        else {}
    )

    agent_result = await run_outreach_agent(lead_dict, analysis_dict)

    outreach = OutreachMessage(
        lead_id=lead.id,
        subject=agent_result.get("subject"),
        email_body=agent_result.get("email_body"),
        follow_up_email=agent_result.get("follow_up_email"),
        linkedin_message=agent_result.get("linkedin_message"),
        call_notes=agent_result.get("call_notes"),
    )
    db.add(outreach)
    await db.flush()

    log = OutreachExecutionLog(
        lead_id=lead.id,
        outreach_message_id=outreach.id,
        agent_reasoning=agent_result.get("agent_reasoning"),
        chosen_channel=agent_result.get("chosen_channel"),
        requires_human_review=agent_result.get("requires_human_review", False),
        review_reason=agent_result.get("review_reason"),
        execution_status="pending",
    )
    db.add(log)
    await db.flush()

    if agent_result.get("requires_human_review"):
        lead.status = "needs_review"

    return {
        "agent_result": agent_result,
        "outreach_id": outreach.id,
        "log_id": log.id,
        "overall_score": analysis_dict.get("overall_score", 0) if analysis_obj else 0,
    }


async def execute_sync_hubspot(lead, db: AsyncSession) -> dict:
    analysis_result = await db.execute(
        select(LeadAnalysis)
        .where(LeadAnalysis.lead_id == lead.id)
        .order_by(LeadAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()

    outreach_result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.lead_id == lead.id)
        .order_by(OutreachMessage.created_at.desc())
        .limit(1)
    )
    outreach = outreach_result.scalar_one_or_none()

    token = get_settings().HUBSPOT_ACCESS_TOKEN
    try:
        contact_id = await hubspot_service.create_or_update_contact(token, lead, analysis)
        await hubspot_service.create_note(token, contact_id, analysis, outreach)
        log = CrmSyncLog(lead_id=lead.id, sync_status="success", external_contact_id=contact_id)
        db.add(log)
        await db.flush()
        return {"status": "success", "contact_id": contact_id}
    except Exception as exc:
        log = CrmSyncLog(lead_id=lead.id, sync_status="failed", error_message=str(exc))
        db.add(log)
        await db.flush()
        return {"status": "failed", "error": str(exc)}


async def execute_create_hubspot_task(lead, db: AsyncSession) -> dict:
    analysis_result = await db.execute(
        select(LeadAnalysis)
        .where(LeadAnalysis.lead_id == lead.id)
        .order_by(LeadAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()

    crm_result = await db.execute(
        select(CrmSyncLog)
        .where(CrmSyncLog.lead_id == lead.id)
        .order_by(CrmSyncLog.created_at.desc())
        .limit(1)
    )
    crm_log = crm_result.scalar_one_or_none()
    if crm_log is None or crm_log.external_contact_id is None:
        return {"status": "skipped", "reason": "no contact id"}

    token = get_settings().HUBSPOT_ACCESS_TOKEN
    try:
        recommended = analysis.recommended_action if analysis else ""
        task_id = await hubspot_service.create_task(token, crm_log.external_contact_id, recommended or "")
        return {"status": "success", "task_id": task_id}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


async def execute_mark_needs_review(lead, db: AsyncSession) -> dict:
    lead.status = "needs_review"
    return {"status": "flagged"}


async def execute_skip_outreach(lead, db: AsyncSession) -> dict:
    lead.status = "skipped"
    return {"status": "skipped"}


_DISPATCH = {
    "analyze_lead": execute_analyze_lead,
    "run_outreach_agent": execute_run_outreach_agent,
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

    existing_metrics = await db.execute(
        select(AutomationMetrics).where(AutomationMetrics.lead_id == lead_id).limit(1)
    )
    if existing_metrics.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=400,
            detail="Agent has already been run on this lead. Each lead can only be processed once.",
        )

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
        try:
            result = await executor(lead, db)
            actions_executed.append(action)
            results[action] = result
        except Exception as exc:
            _logger.error("Executor %s failed: %s", action, exc)
            results[action] = {"status": "error", "detail": str(exc)}
            continue

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

    if "run_outreach_agent" in actions_executed:
        result_data = results.get("run_outreach_agent", {})
        agent_result = result_data.get("agent_result", {})
        log_id = result_data.get("log_id")

        # Re-fetch log to update execution_status
        log = await db.get(OutreachExecutionLog, log_id) if log_id else None

        chosen_channel = agent_result.get("chosen_channel") or ""
        overall_score = result_data.get("overall_score") or 0

        new_status = "pending"
        if log and not agent_result.get("requires_human_review"):
            if chosen_channel in ("email", "both"):
                sent = await asyncio.to_thread(
                    gmail_service.send_email,
                    lead.email,
                    agent_result.get("subject") or "",
                    agent_result.get("email_body") or "",
                )
                new_status = "sent" if sent else "failed"
            if chosen_channel in ("linkedin", "both"):
                new_status = "pending_manual"
            log.execution_status = new_status
            await db.commit()

            if overall_score >= 70:
                await slack_service.send_alert(slack_service.build_lead_alert(
                    first_name=lead.first_name,
                    last_name=lead.last_name,
                    company=lead.company or "",
                    overall_score=overall_score,
                    chosen_channel=chosen_channel,
                    recommended_action=results.get("analyze_lead", {}).get("recommended_action") or "",
                    lead_id=lead_id,
                ))
        elif log and agent_result.get("requires_human_review"):
            await slack_service.send_alert(slack_service.build_review_alert(
                first_name=lead.first_name,
                last_name=lead.last_name,
                company=lead.company or "",
                overall_score=overall_score,
                review_reason=agent_result.get("review_reason"),
                lead_id=lead_id,
            ))

        # HubSpot note if contact exists
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
                channel = agent_result.get("chosen_channel") or "unknown"
                exec_status = (log.execution_status if log else "unknown")
                linkedin_pending = "LinkedIn message pending manual send." if chosen_channel in ("linkedin", "both") else ""
                note = f"Outreach agent executed.\nChannel: {channel}\nEmail status: {exec_status}\n{linkedin_pending}".strip()
                await hubspot_service.create_call_note(token, crm_sync.external_contact_id, note)
            except Exception as exc:
                _logger.warning("HubSpot outreach note failed for lead %s: %s", lead_id, exc)

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
