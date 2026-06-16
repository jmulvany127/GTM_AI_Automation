from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AutomationMetrics(Base):
    __tablename__ = "automation_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"))
    workflow_name: Mapped[str] = mapped_column(String(100), server_default="gtm_workflow")
    actions_executed: Mapped[str | None] = mapped_column(Text, default=None)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reasoning_summary: Mapped[str | None] = mapped_column(Text, default=None)
    manual_time_estimate_minutes: Mapped[int] = mapped_column(Integer, server_default="25")
    automated_time_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    estimated_time_saved_minutes: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
