from datetime import datetime
from pydantic import BaseModel


class LeadAnalysisCreate(BaseModel):
    company_summary: str | None = None
    persona_type: str | None = None
    pain_points: str | None = None
    buying_signals: str | None = None
    objections: str | None = None
    fit_score: int | None = None
    urgency_score: int | None = None
    overall_score: int | None = None
    recommended_action: str | None = None
    confidence_score: float | None = None
    raw_ai_json: str | None = None


class LeadAnalysisRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    company_summary: str | None
    persona_type: str | None
    pain_points: str | None
    buying_signals: str | None
    objections: str | None
    fit_score: int | None
    urgency_score: int | None
    overall_score: int | None
    recommended_action: str | None
    confidence_score: float | None
    raw_ai_json: str | None
    created_at: datetime
