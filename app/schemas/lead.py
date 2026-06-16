from datetime import datetime
from pydantic import BaseModel, EmailStr


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    company: str | None = None
    job_title: str | None = None
    company_website: str | None = None
    source: str | None = None
    notes: str | None = None


class LeadRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    first_name: str
    last_name: str
    email: str
    company: str | None
    job_title: str | None
    company_website: str | None
    source: str | None
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class LeadUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    company: str | None = None
    job_title: str | None = None
    company_website: str | None = None
    source: str | None = None
    notes: str | None = None
    status: str | None = None
