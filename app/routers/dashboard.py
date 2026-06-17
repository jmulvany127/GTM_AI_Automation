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
from app.models.outreach import OutreachMessage
from app.services import metrics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/leads", response_class=HTMLResponse)
async def dashboard_leads(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).order_by(desc(Lead.created_at)))
    leads = result.scalars().all()

    lead_rows = []
    for lead in leads:
        analysis_result = await db.execute(
            select(LeadAnalysis)
            .where(LeadAnalysis.lead_id == lead.id)
            .order_by(desc(LeadAnalysis.created_at))
            .limit(1)
        )
        analysis = analysis_result.scalar_one_or_none()
        lead_rows.append({
            "lead": lead,
            "overall_score": analysis.overall_score if analysis else None,
        })

    return templates.TemplateResponse(request, "leads.html", {"leads": lead_rows})


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

    crm_result = await db.execute(
        select(CrmSyncLog)
        .where(CrmSyncLog.lead_id == lead_id)
        .order_by(desc(CrmSyncLog.created_at))
        .limit(1)
    )
    crm_sync = crm_result.scalar_one_or_none()

    return templates.TemplateResponse(
        request,
        "lead_detail.html",
        {
            "lead": lead,
            "analysis": analysis,
            "outreach": outreach,
            "crm_sync": crm_sync,
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

    rows = []
    for analysis in analyses:
        lead = None
        if analysis.lead_id is not None:
            lead = await db.get(Lead, analysis.lead_id)
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
