from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.connectors.base import ConnectorRecord


@dataclass(slots=True)
class MatchResult:
    score: float
    relevance_label: str
    confidence: str
    why_it_surfaced: list[str] = field(default_factory=list)
    why_it_may_not_fit: list[str] = field(default_factory=list)
    matching_gaps: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)


def _clean_text(value: str | None) -> str:
    return (value or "").lower()


def evaluate(profile: Any, record: ConnectorRecord, *, is_new: bool = True) -> MatchResult:
    score = 0.0
    surfaced: list[str] = []
    cautions: list[str] = list(record.gaps)
    debug: dict[str, Any] = {"weights": {}}

    haystack = " ".join(
        [
            _clean_text(record.title),
            _clean_text(record.summary),
            " ".join(_clean_text(tag) for tag in record.tags),
            _clean_text(record.location_summary),
        ]
    )

    def add(points: float, key: str, reason: str) -> None:
        nonlocal score
        score += points
        debug["weights"][key] = points
        surfaced.append(reason)

    if profile.cancer_type and _clean_text(profile.cancer_type) in haystack:
        add(30, "cancer_type", f"The source directly mentions {profile.cancer_type}.")
    else:
        cautions.append("The source did not clearly state the entered cancer type.")

    if profile.subtype and _clean_text(profile.subtype) in haystack:
        add(10, "subtype", f"The source also mentions the subtype or disease framing: {profile.subtype}.")

    biomarker_hits: list[str] = []
    for biomarker in getattr(profile, "biomarkers", []):
        marker_terms = [biomarker.name, biomarker.variant]
        marker_phrase = " ".join(part for part in marker_terms if part)
        if marker_phrase and _clean_text(marker_phrase) in haystack:
            biomarker_hits.append(marker_phrase)
        elif biomarker.name and _clean_text(biomarker.name) in haystack:
            biomarker_hits.append(biomarker.name)
    if biomarker_hits:
        biomarker_points = min(25, 12 + (len(biomarker_hits) - 1) * 6)
        add(biomarker_points, "biomarkers", f"Possible biomarker overlap: {', '.join(sorted(set(biomarker_hits)))}.")
    elif getattr(profile, "biomarkers", []):
        cautions.append("The source did not clearly mention the entered biomarker details.")

    if profile.stage_or_context and _clean_text(profile.stage_or_context) in haystack:
        add(10, "stage", f"The disease context may line up with the entered stage/context: {profile.stage_or_context}.")

    therapy_hits: list[str] = []
    for therapy in getattr(profile, "therapy_history", []):
        if therapy.therapy_name and _clean_text(therapy.therapy_name) in haystack:
            therapy_hits.append(therapy.therapy_name)
    if therapy_hits:
        add(10, "prior_therapy", f"The source references prior therapy context such as {', '.join(sorted(set(therapy_hits)))}.")

    preferences = getattr(profile, "would_consider", []) or []
    preference_hits = [item for item in preferences if _clean_text(item) in haystack]
    if preference_hits:
        add(5, "preferences", f"It overlaps with the entered preferences: {', '.join(preference_hits)}.")

    exclusions = getattr(profile, "would_not_consider", []) or []
    exclusion_hits = [item for item in exclusions if _clean_text(item) in haystack]
    if exclusion_hits:
        score -= 10
        debug["weights"]["exclusions"] = -10
        cautions.append(f"It may conflict with entered exclusions: {', '.join(exclusion_hits)}.")

    if record.category == "clinical_trials":
        if "recruiting" in haystack or "enrolling" in haystack:
            add(5, "recruitment", "The trial appears to be open or recruiting.")
        else:
            cautions.append("Recruitment status was not clearly open in the retrieved summary.")
        if profile.location_label and record.location_summary:
            same_region = any(token.lower() in record.location_summary.lower() for token in profile.location_label.split())
            if same_region or "remote" in record.location_summary.lower():
                add(5, "geography", "The location may be feasible based on the entered travel area or remote prescreening.")

    if is_new:
        add(5, "novelty", "This appears to be new since the last stored version.")

    if score >= 70:
        relevance = "High relevance"
        confidence = "medium"
    elif score >= 45:
        relevance = "Worth reviewing"
        confidence = "medium"
    elif score >= 25:
        relevance = "Low confidence"
        confidence = "low"
    else:
        relevance = "Insufficient data"
        confidence = "low"

    if len(surfaced) >= 4 and score >= 70:
        confidence = "high"

    return MatchResult(
        score=round(max(score, 0.0), 1),
        relevance_label=relevance,
        confidence=confidence,
        why_it_surfaced=surfaced,
        why_it_may_not_fit=cautions,
        matching_gaps=cautions,
        debug=debug,
    )
