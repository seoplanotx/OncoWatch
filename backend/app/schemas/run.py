from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.finding import FindingRead


class MonitoringRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int | None = None
    status: str
    triggered_by: str
    started_at: datetime
    completed_at: datetime | None = None
    summary_json: dict = Field(default_factory=dict)
    new_findings_count: int
    changed_findings_count: int
    sources_checked: list[str] = Field(default_factory=list)
    error_text: str | None = None


class TriggerRunRequest(BaseModel):
    profile_id: int | None = None
    triggered_by: str = "manual"


class BriefingFindingSection(BaseModel):
    key: str
    title: str
    description: str
    empty_message: str
    count: int
    items: list[FindingRead] = Field(default_factory=list)


class BriefingBlocker(BaseModel):
    label: str
    finding_count: int
    examples: list[str] = Field(default_factory=list)


class BriefingSnapshot(BaseModel):
    latest_run_started_at: datetime | None = None
    latest_run_completed_at: datetime | None = None
    new_count: int = 0
    changed_count: int = 0
    sections: list[BriefingFindingSection] = Field(default_factory=list)
    blockers: list[BriefingBlocker] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    latest_run: MonitoringRunRead | None = None
    next_scheduled_run: str | None = None
    counts: dict = Field(default_factory=dict)
    recent_findings: list[FindingRead] = Field(default_factory=list)
    briefing: BriefingSnapshot = Field(default_factory=BriefingSnapshot)
    disclaimer: str
