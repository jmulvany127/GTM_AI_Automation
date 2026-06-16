from datetime import datetime
from unittest.mock import MagicMock
from app.schemas.analysis import LeadAnalysisCreate, LeadAnalysisRead


def test_lead_analysis_create_all_fields_optional():
    schema = LeadAnalysisCreate()
    assert schema.company_summary is None
    assert schema.fit_score is None
    assert schema.confidence_score is None
    assert schema.raw_ai_json is None


def test_lead_analysis_create_accepts_all_fields():
    schema = LeadAnalysisCreate(
        company_summary="A SaaS company",
        persona_type="Champion",
        pain_points="Manual processes",
        buying_signals="Requested demo",
        objections="Budget concerns",
        fit_score=75,
        urgency_score=60,
        overall_score=70,
        recommended_action="Schedule call",
        confidence_score=0.8,
        raw_ai_json='{"fit_score": 75}',
    )
    assert schema.fit_score == 75
    assert schema.confidence_score == 0.8


def test_lead_analysis_read_from_orm_object():
    obj = MagicMock()
    obj.id = 1
    obj.lead_id = 42
    obj.company_summary = "A SaaS company"
    obj.persona_type = "Champion"
    obj.pain_points = "Manual processes"
    obj.buying_signals = "Requested demo"
    obj.objections = "Budget"
    obj.fit_score = 75
    obj.urgency_score = 60
    obj.overall_score = 70
    obj.recommended_action = "Schedule call"
    obj.confidence_score = 0.8
    obj.raw_ai_json = '{"fit_score": 75}'
    obj.created_at = datetime(2026, 6, 16, 12, 0, 0)

    result = LeadAnalysisRead.model_validate(obj)
    assert result.id == 1
    assert result.lead_id == 42
    assert result.fit_score == 75
    assert result.confidence_score == 0.8
    assert result.created_at == datetime(2026, 6, 16, 12, 0, 0)
