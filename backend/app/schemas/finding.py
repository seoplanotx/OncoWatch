from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


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

    def _record_payload(self) -> dict:
        payload = self.match_debug.get("record_payload") if isinstance(self.match_debug, dict) else None
        return payload if isinstance(payload, dict) else {}

    @computed_field
    @property
    def primary_evidence_label(self) -> str | None:
        return self.evidence_items[0].label if self.evidence_items else None

    @computed_field
    @property
    def primary_evidence_snippet(self) -> str | None:
        return self.evidence_items[0].snippet if self.evidence_items else None

    @computed_field
    @property
    def trial_recruitment_status(self) -> str | None:
        status = self._record_payload().get("recruitment_status")
        if status is None:
            return None
        return str(status).strip() or None

    @computed_field
    @property
    def trial_phases(self) -> list[str]:
        phases = self._record_payload().get("phases")
        if not isinstance(phases, list):
            return []
        return [str(phase).strip() for phase in phases if str(phase).strip()]

    @computed_field
    @property
    def trial_sponsor(self) -> str | None:
        sponsor = self._record_payload().get("sponsor")
        if sponsor is None:
            return None
        return str(sponsor).strip() or None

    @computed_field
    @property
    def trial_intervention_summary(self) -> str | None:
        interventions = self._record_payload().get("interventions")
        if not isinstance(interventions, list):
            return None
        cleaned = [str(item).strip() for item in interventions if str(item).strip()]
        if not cleaned:
            return None
        return ", ".join(cleaned[:3])


class FindingsQueryResponse(BaseModel):
    total: int
    items: list[FindingRead]
