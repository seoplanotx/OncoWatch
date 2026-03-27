from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportGenerateRequest(BaseModel):
    profile_id: int | None = None
    report_type: str = "daily_summary"


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
