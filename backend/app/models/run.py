from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.dates import utcnow

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.profile import PatientProfile


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("patient_profiles.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    triggered_by: Mapped[str] = mapped_column(String(40), default="manual")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    new_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    changed_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    sources_checked: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped["PatientProfile | None"] = relationship(back_populates="monitoring_runs")
    findings: Mapped[list["Finding"]] = relationship(back_populates="monitoring_run")
