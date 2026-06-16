from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class LeadAnalysis(Base):
    __tablename__ = "lead_analysis"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"))
    company_summary: Mapped[str | None] = mapped_column(Text, default=None)
    persona_type: Mapped[str | None] = mapped_column(String(100), default=None)
    pain_points: Mapped[str | None] = mapped_column(Text, default=None)
    buying_signals: Mapped[str | None] = mapped_column(Text, default=None)
    objections: Mapped[str | None] = mapped_column(Text, default=None)
    fit_score: Mapped[int | None] = mapped_column(Integer, default=None)
    urgency_score: Mapped[int | None] = mapped_column(Integer, default=None)
    overall_score: Mapped[int | None] = mapped_column(Integer, default=None)
    recommended_action: Mapped[str | None] = mapped_column(Text, default=None)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=None)
    raw_ai_json: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
