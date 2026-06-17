from datetime import datetime
from pydantic import BaseModel, field_validator


class CallAnalysisRequest(BaseModel):
    lead_id: int | None = None
    transcript: str

    @field_validator("transcript")
    @classmethod
    def transcript_min_length(cls, v: str) -> str:
        if len(v) < 50:
            raise ValueError("transcript must be at least 50 characters")
        return v


class CallAnalysisResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int | None = None
    pain_points: str | None = None
    objections: str | None = None
    competitors: str | None = None
    budget_signals: str | None = None
    decision_timeline: str | None = None
    buying_intent_score: float | None = None
    recommended_follow_up: str | None = None
    crm_note: str | None = None
    follow_up_email: str | None = None
    created_at: datetime
