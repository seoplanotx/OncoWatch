from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReportType = Literal["daily_summary", "full_review", "appointment_prep"]


class ReportGenerateRequest(BaseModel):
    profile_id: int | None = None
    report_type: ReportType = "daily_summary"
    # Appointment prep only; printed on the PDF, never persisted to the DB.
    appointment_date: date | None = None
    appointment_clinician: str | None = Field(None, max_length=120)


class ReportOutlineItem(BaseModel):
    id: int
    title: str
    source_name: str
    source_url: str | None = None
    identifier: str = ""
    relevance_label: str = ""
    status: str = ""
    status_line: str = ""
    why_it_surfaced: str | None = None
    saved_for_discussion: bool = False


class ReportOutlineSection(BaseModel):
    key: str
    title: str
    description: str
    empty_message: str
    count: int
    items: list[ReportOutlineItem] = Field(default_factory=list)


class ReportOutlineGap(BaseModel):
    label: str
    finding_count: int
    examples: list[str] = Field(default_factory=list)


class ReportOutline(BaseModel):
    """What a report contains — the same view whether it exists yet or not."""

    report_type: str
    report_title: str
    sections: list[ReportOutlineSection] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    gaps: list[ReportOutlineGap] = Field(default_factory=list)
    counts: dict = Field(default_factory=dict)


class ReportExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int | None = None
    report_type: str
    status: str
    file_path: str
    generated_at: datetime
    summary_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    # Computed by the routes, not stored: whether the PDF is still on disk.
    file_exists: bool = True


class ReportListRead(BaseModel):
    items: list[ReportExportRead] = Field(default_factory=list)
    # Reports belonging to non-active profiles, hidden from this view.
    other_profiles_count: int = 0
