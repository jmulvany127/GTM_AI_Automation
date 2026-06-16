from app.models.lead import Lead


def test_lead_model_defaults():
    lead = Lead(first_name="John", last_name="Doe", email="john@example.com")
    assert lead.first_name == "John"
    assert lead.last_name == "Doe"
    assert lead.email == "john@example.com"
    assert lead.status == "new"
    assert lead.company is None
    assert lead.job_title is None
