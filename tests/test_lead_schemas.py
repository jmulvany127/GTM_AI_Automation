import pytest
from datetime import datetime
from pydantic import ValidationError
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate


def test_lead_create_requires_first_name():
    with pytest.raises(ValidationError):
        LeadCreate(last_name="Doe", email="j@example.com")


def test_lead_create_requires_last_name():
    with pytest.raises(ValidationError):
        LeadCreate(first_name="John", email="j@example.com")


def test_lead_create_requires_email():
    with pytest.raises(ValidationError):
        LeadCreate(first_name="John", last_name="Doe")


def test_lead_create_rejects_invalid_email():
    with pytest.raises(ValidationError):
        LeadCreate(first_name="John", last_name="Doe", email="not-an-email")


def test_lead_create_optional_fields_default_to_none():
    lead = LeadCreate(first_name="John", last_name="Doe", email="j@example.com")
    assert lead.company is None
    assert lead.job_title is None
    assert lead.company_website is None
    assert lead.source is None
    assert lead.notes is None


def test_lead_update_all_fields_optional():
    update = LeadUpdate()
    assert update.first_name is None
    assert update.company is None
    assert update.status is None


def test_lead_read_from_attributes():
    now = datetime(2024, 1, 1, 12, 0, 0)
    lead = LeadRead(
        id=1,
        first_name="John",
        last_name="Doe",
        email="j@example.com",
        company=None,
        job_title=None,
        company_website=None,
        source=None,
        notes=None,
        status="new",
        created_at=now,
        updated_at=now,
    )
    assert lead.id == 1
    assert lead.status == "new"
