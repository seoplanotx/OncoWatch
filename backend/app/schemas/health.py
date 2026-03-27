from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthCheckItem(BaseModel):
    key: str
    label: str
    ok: bool
    message: str


class HealthCheckResponse(BaseModel):
    checked_at: datetime
    overall_ok: bool
    items: list[HealthCheckItem] = Field(default_factory=list)
