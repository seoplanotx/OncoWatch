from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.utils.dates import utcnow

if TYPE_CHECKING:
    from app.models.profile import PatientProfile
    from app.models.run import MonitoringRun


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("profile_id", "source_name", "external_identifier", name="uq_finding_profile_source_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False)
    monitoring_run_id: Mapped[int | None] = mapped_column(ForeignKey("monitoring_runs.id", ondelete="SET NULL"), nullable=True)

    type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    external_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    structured_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_surfaced: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_may_not_fit: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(40), default="low")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_label: Mapped[str] = mapped_column(String(40), default="Insufficient data")
    status: Mapped[str] = mapped_column(String(40), default="new")

    location_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matching_gaps: Mapped[list[str]] = mapped_column(JSON, default=list)
    match_debug: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    llm_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    llm_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    profile: Mapped["PatientProfile"] = relationship(back_populates="findings")
    monitoring_run: Mapped["MonitoringRun | None"] = relationship(back_populates="findings")
    evidence_items: Mapped[list["FindingEvidence"]] = relationship(
        back_populates="finding",
        cascade="all, delete-orphan",
        order_by="FindingEvidence.id",
    )


class FindingEvidence(Base, TimestampMixin):
    __tablename__ = "finding_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    finding: Mapped["Finding"] = relationship(back_populates="evidence_items")
