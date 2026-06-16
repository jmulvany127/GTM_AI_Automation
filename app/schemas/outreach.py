from datetime import datetime
from pydantic import BaseModel


class OutreachCreate(BaseModel):
    subject: str | None = None
    email_body: str | None = None
    follow_up_email: str | None = None
    linkedin_message: str | None = None
    call_notes: str | None = None


class OutreachRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    subject: str | None
    email_body: str | None
    follow_up_email: str | None
    linkedin_message: str | None
    call_notes: str | None
    created_at: datetime
