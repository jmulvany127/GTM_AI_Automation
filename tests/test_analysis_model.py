from app.models.analysis import LeadAnalysis


def test_lead_analysis_tablename():
    assert LeadAnalysis.__tablename__ == "lead_analysis"


def test_lead_analysis_columns():
    col_names = {c.name for c in LeadAnalysis.__table__.columns}
    assert col_names == {
        "id", "lead_id", "company_summary", "persona_type",
        "pain_points", "buying_signals", "objections",
        "fit_score", "urgency_score", "overall_score",
        "recommended_action", "confidence_score", "raw_ai_json", "created_at",
    }


def test_lead_analysis_has_foreign_key_to_leads():
    fk_targets = {fk.target_fullname for fk in LeadAnalysis.__table__.foreign_keys}
    assert "leads.id" in fk_targets


def test_lead_analysis_defaults_to_none():
    analysis = LeadAnalysis(lead_id=1)
    assert analysis.company_summary is None
    assert analysis.fit_score is None
    assert analysis.confidence_score is None
