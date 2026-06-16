from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    company_website: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    source: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(50), server_default="new")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.status is None:
            self.status = "new"
