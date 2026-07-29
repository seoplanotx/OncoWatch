from __future__ import annotations

from pydantic import BaseModel, Field


class CaseBiomarker(BaseModel):
    name: str
    variant: str | None = None
    status: str | None = None


class CaseTherapyLine(BaseModel):
    therapy_name: str
    therapy_type: str | None = None
    line_of_therapy: str | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class CaseHeader(BaseModel):
    cancer_type: str
    subtype: str | None = None
    stage_or_context: str | None = None
    current_therapy_status: str | None = None
    location_label: str | None = None
    travel_radius_miles: int | None = None
    biomarkers: list[CaseBiomarker] = Field(default_factory=list)
    lines_of_therapy: list[CaseTherapyLine] = Field(default_factory=list)
    would_consider: list[str] = Field(default_factory=list)
    would_not_consider: list[str] = Field(default_factory=list)


class CaseFramingGeneration(BaseModel):
    mode: str
    status: str
    provider: str | None = None
    model: str | None = None
    message: str | None = None


class CaseFraming(BaseModel):
    text: str
    generation: CaseFramingGeneration


class CondensedFinding(BaseModel):
    id: int
    type: str
    title: str
    source_name: str
    source_url: str | None = None
    identifier: str
    relevance_label: str
    score: float
    status: str
    recruitment_bucket: str | None = None
    freshness_bucket: str | None = None
    why_it_surfaced: str | None = None
    why_it_may_not_fit: str | None = None
    matching_gaps: list[str] = Field(default_factory=list)
    user_action: str = "none"


class DataGap(BaseModel):
    label: str
    finding_count: int
    examples: list[str] = Field(default_factory=list)
    example_identifiers: list[str] = Field(default_factory=list)


class ClinicianSummaryRead(BaseModel):
    generated_at: str
    case_header: CaseHeader
    case_framing: CaseFraming
    trial_findings: list[CondensedFinding] = Field(default_factory=list)
    research_findings: list[CondensedFinding] = Field(default_factory=list)
    discussion_questions: list[str] = Field(default_factory=list)
    data_gaps: list[DataGap] = Field(default_factory=list)
    disclaimer: str
