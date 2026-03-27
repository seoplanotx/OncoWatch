from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.run import MonitoringRun


class PatientProfile(Base, TimestampMixin):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_name: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    cancer_type: Mapped[str] = mapped_column(String(120), nullable=False)
    subtype: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stage_or_context: Mapped[str | None] = mapped_column(String(120), nullable=True)
    current_therapy_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_radius_miles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    would_consider: Mapped[list[str]] = mapped_column(JSON, default=list)
    would_not_consider: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    biomarkers: Mapped[list["Biomarker"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Biomarker.id",
    )
    therapy_history: Mapped[list["TherapyHistoryEntry"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="TherapyHistoryEntry.id",
    )
    findings: Mapped[list["Finding"]] = relationship(back_populates="profile")
    monitoring_runs: Mapped[list["MonitoringRun"]] = relationship(back_populates="profile")


class Biomarker(Base, TimestampMixin):
    __tablename__ = "biomarkers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped["PatientProfile"] = relationship(back_populates="biomarkers")


class TherapyHistoryEntry(Base, TimestampMixin):
    __tablename__ = "therapy_history_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False)
    therapy_name: Mapped[str] = mapped_column(String(160), nullable=False)
    therapy_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    line_of_therapy: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped["PatientProfile"] = relationship(back_populates="therapy_history")
