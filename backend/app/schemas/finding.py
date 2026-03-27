from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FindingEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str | None = None
    snippet: str | None = None
    source_url: str | None = None
    source_identifier: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: int
    monitoring_run_id: int | None = None
    type: str
    title: str
    source_name: str
    source_url: str | None = None
    external_identifier: str
    retrieved_at: datetime
    published_at: datetime | None = None
    structured_tags: list[str] = Field(default_factory=list)
    raw_summary: str | None = None
    normalized_summary: str | None = None
    why_it_surfaced: str | None = None
    why_it_may_not_fit: str | None = None
    confidence: str
    score: float
    relevance_label: str
    status: str
    location_summary: str | None = None
    matching_gaps: list[str] = Field(default_factory=list)
    match_debug: dict = Field(default_factory=dict)
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_metadata: dict = Field(default_factory=dict)
    evidence_items: list[FindingEvidenceRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class FindingsQueryResponse(BaseModel):
    total: int
    items: list[FindingRead]
