from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class OutreachExecutionLog(Base):
    __tablename__ = "outreach_execution_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"), nullable=False)
    outreach_message_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("outreach_messages.id"), default=None)
    agent_reasoning: Mapped[str | None] = mapped_column(Text, default=None)
    chosen_channel: Mapped[str | None] = mapped_column(String(50), default=None)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    review_reason: Mapped[str | None] = mapped_column(Text, default=None)
    execution_status: Mapped[str] = mapped_column(String(50), server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
