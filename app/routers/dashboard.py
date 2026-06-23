import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import LeadAnalysis
from app.models.call_analysis import CallAnalysis
from app.models.crm_log import CrmSyncLog
from app.models.lead import Lead
from app.models.metrics import AutomationMetrics
from app.models.outreach import OutreachMessage
from app.models.outreach_execution_log import OutreachExecutionLog
from app.services import metrics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


def _fmt_field(value: str | None) -> str:
    """Render a stored field value for display.

    Fields are stored as either plain strings or JSON-encoded arrays/objects.
    Arrays are rendered as a bullet list; objects as "Key: value" lines.
    """
    if not value:
        return "—"
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value
    if isinstance(parsed, list):
        return "\n".join(f"• {item}" for item in parsed) if parsed else "—"
    if isinstance(parsed, dict):
        lines = []
        for k, v in parsed.items():
            label = k.replace("_", " ").title()
            lines.append(f"{label}: {v}")
        return "\n".join(lines) if lines else "—"
    return str(parsed)


templates.env.filters["fmt_field"] = _fmt_field


@router.get("/leads", response_class=HTMLResponse)
async def dashboard_leads(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).order_by(desc(Lead.created_at)))
    leads = result.scalars().all()

    lead_ids = [lead.id for lead in leads]

    # Batch-fetch latest analysis scores for all leads in one query
    analysis_scores: dict[int, int | None] = {}
    if lead_ids:
        analysis_result = await db.execute(
            select(LeadAnalysis).where(LeadAnalysis.lead_id.in_(lead_ids))
        )
        for analysis in analysis_result.scalars().all():
            # Keep only the highest-id (most recent) per lead
            if analysis.lead_id not in analysis_scores:
                analysis_scores[analysis.lead_id] = analysis.overall_score

    # Batch-fetch all automation_metrics records in one query to determine processed leads
    processed_lead_ids: set[int] = set()
    if lead_ids:
        metrics_result = await db.execute(
            select(AutomationMetrics.lead_id).where(AutomationMetrics.lead_id.in_(lead_ids))
        )
        processed_lead_ids = {row for row in metrics_result.scalars().all()}

    lead_rows = []
    for lead in leads:
        lead_rows.append({
            "lead": lead,
            "overall_score": analysis_scores.get(lead.id),
            "agent_run": lead.id in processed_lead_ids,
        })

    return templates.TemplateResponse(request, "leads.html", {"leads": lead_rows})


@router.get("/leads/new", response_class=HTMLResponse)
async def dashboard_lead_new(request: Request):
    return templates.TemplateResponse(request, "lead_form.html", {})


@router.get("/leads/{lead_id}", response_class=HTMLResponse)
async def dashboard_lead_detail(lead_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    analysis_result = await db.execute(
        select(LeadAnalysis)
        .where(LeadAnalysis.lead_id == lead_id)
        .order_by(desc(LeadAnalysis.created_at))
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()

    outreach_result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.lead_id == lead_id)
        .order_by(desc(OutreachMessage.created_at))
        .limit(1)
    )
    outreach = outreach_result.scalar_one_or_none()

    execution_log_result = await db.execute(
        select(OutreachExecutionLog)
        .where(OutreachExecutionLog.lead_id == lead_id)
        .order_by(desc(OutreachExecutionLog.created_at))
        .limit(1)
    )
    execution_log = execution_log_result.scalar_one_or_none()

    crm_result = await db.execute(
        select(CrmSyncLog)
        .where(CrmSyncLog.lead_id == lead_id)
        .order_by(desc(CrmSyncLog.created_at))
        .limit(1)
    )
    crm_sync = crm_result.scalar_one_or_none()

    call_analyses_result = await db.execute(
        select(CallAnalysis)
        .where(CallAnalysis.lead_id == lead_id)
        .order_by(desc(CallAnalysis.created_at))
    )
    call_analyses = call_analyses_result.scalars().all()

    agent_run_result = await db.execute(
        select(AutomationMetrics)
        .where(AutomationMetrics.lead_id == lead_id)
        .order_by(desc(AutomationMetrics.created_at))
        .limit(1)
    )
    agent_run = agent_run_result.scalar_one_or_none()

    return templates.TemplateResponse(
        request,
        "lead_detail.html",
        {
            "lead": lead,
            "analysis": analysis,
            "outreach": outreach,
            "execution_log": execution_log,
            "crm_sync": crm_sync,
            "call_analyses": call_analyses,
            "agent_run": agent_run,
        },
    )


@router.get("/metrics", response_class=HTMLResponse)
async def dashboard_metrics(request: Request, db: AsyncSession = Depends(get_db)):
    metrics = await metrics_service.get_roi_metrics(db)
    return templates.TemplateResponse(request, "metrics.html", {"metrics": metrics})


@router.get("/call-notes", response_class=HTMLResponse)
async def dashboard_call_notes_list(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CallAnalysis).order_by(desc(CallAnalysis.created_at)))
    analyses = result.scalars().all()

    # Batch-fetch all referenced leads in one query
    lead_ids = {a.lead_id for a in analyses if a.lead_id is not None}
    leads_by_id: dict[int, Lead] = {}
    if lead_ids:
        leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
        for lead in leads_result.scalars().all():
            leads_by_id[lead.id] = lead

    rows = []
    for analysis in analyses:
        lead = leads_by_id.get(analysis.lead_id) if analysis.lead_id else None
        rows.append({"analysis": analysis, "lead": lead})

    linked_lead_ids_result = await db.execute(
        select(distinct(CallAnalysis.lead_id)).where(CallAnalysis.lead_id != None)
    )
    linked_lead_ids = linked_lead_ids_result.scalars().all()
    all_leads_result = await db.execute(
        select(Lead).where(Lead.id.in_(linked_lead_ids)).order_by(Lead.first_name)
    )
    all_leads = all_leads_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "call_notes_list.html",
        {"analyses": rows, "all_leads": all_leads},
    )


@router.get("/call-notes/new", response_class=HTMLResponse)
async def dashboard_call_notes_new(
    request: Request,
    lead_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Lead).order_by(Lead.first_name))
    all_leads = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "call_notes_new.html",
        {"all_leads": all_leads, "preselected_lead_id": lead_id}
    )


@router.get("/call-notes/{analysis_id}", response_class=HTMLResponse)
async def dashboard_call_analysis(analysis_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    analysis = await db.get(CallAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Call analysis not found")
    lead = None
    if analysis.lead_id is not None:
        lead = await db.get(Lead, analysis.lead_id)
    return templates.TemplateResponse(
        request,
        "call_analysis.html",
        {"analysis": analysis, "lead": lead}
    )
