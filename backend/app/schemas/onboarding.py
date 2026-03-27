from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OnboardingStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_completed: bool
    completed_at: datetime | None = None
    current_step: str | None = None
    show_demo_profile_option: bool
    welcome_acknowledged: bool
    last_health_check: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class OnboardingCompleteRequest(BaseModel):
    current_step: str | None = None
    welcome_acknowledged: bool = True
    is_completed: bool = True


class DemoProfileResponse(BaseModel):
    profile_id: int
