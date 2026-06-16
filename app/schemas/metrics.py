from datetime import datetime
from pydantic import BaseModel


class AutomationMetricsRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    workflow_name: str
    actions_executed: str | None
    requires_human_review: bool
    reasoning_summary: str | None
    manual_time_estimate_minutes: int
    automated_time_seconds: float | None
    estimated_time_saved_minutes: float | None
    created_at: datetime
