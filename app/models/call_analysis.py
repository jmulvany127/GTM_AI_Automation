from datetime import datetime
from sqlalchemy import Text, DateTime, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CallAnalysis(Base):
    __tablename__ = "call_analysis"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("leads.id"), nullable=True, default=None)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    pain_points: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    objections: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    competitors: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    budget_signals: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    decision_timeline: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    buying_intent_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    recommended_follow_up: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    crm_note: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    follow_up_email: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
