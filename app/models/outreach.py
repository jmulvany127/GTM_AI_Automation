from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"))
    subject: Mapped[str | None] = mapped_column(String(500), default=None)
    email_body: Mapped[str | None] = mapped_column(Text, default=None)
    follow_up_email: Mapped[str | None] = mapped_column(Text, default=None)
    linkedin_message: Mapped[str | None] = mapped_column(Text, default=None)
    call_notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
