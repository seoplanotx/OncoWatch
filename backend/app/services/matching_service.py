from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.connectors.base import ConnectorRecord
from app.services.normalization_service import (
    build_normalized_summary,
    dedupe,
    normalize_profile,
    normalize_record,
)


@dataclass(slots=True)
class MatchResult:
    score: float
    relevance_label: str
    confidence: str
    why_it_surfaced: list[str] = field(default_factory=list)
    why_it_may_not_fit: list[str] = field(default_factory=list)
    matching_gaps: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)
    normalized_summary: str | None = None
    normalized_facts: dict[str, Any] = field(default_factory=dict)


def evaluate(profile: Any, record: ConnectorRecord, *, is_new: bool = True) -> MatchResult:
    profile_facts = normalize_profile(profile)
    record_facts = normalize_record(record, profile_facts)

    score = 0.0
    surfaced: list[str] = []
    cautions: list[str] = []
    gaps: list[str] = list(record_facts.missing_fields)
    debug: dict[str, Any] = {
        "weights": {},
        "rules": [],
        "profile_facts": profile_facts.as_dict(),
        "record_facts": record_facts.as_dict(),
        "record_payload": record.raw_payload,
    }

    def add(points: float, key: str, reason: str, *, surfaced_reason: bool = True) -> None:
        nonlocal score
        score += points
        debug["weights"][key] = round(debug["weights"].get(key, 0.0) + points, 1)
        debug["rules"].append({"rule": key, "points": points, "reason": reason})
        if surfaced_reason:
            surfaced.append(reason)

    if record_facts.cancer_terms:
        add(35, "cancer_type", f"The source directly matches the main cancer context: {', '.join(record_facts.cancer_terms)}.")
    else:
        cautions.append("The source did not clearly match the main cancer type that was entered.")

    if record_facts.subtype_terms:
        add(12, "subtype", f"The source also matches the disease subtype terms: {', '.join(record_facts.subtype_terms)}.")

    biomarker_hits = dedupe([*record_facts.biomarker_terms, *record_facts.biomarker_genes])
    exact_biomarker_hits = [term for term in record_facts.biomarker_terms if term in set(profile_facts.biomarker_terms)]
    gene_only_hits = [term for term in record_facts.biomarker_genes if term not in set(exact_biomarker_hits)]
    if exact_biomarker_hits:
        biomarker_points = min(32, 18 + (len(exact_biomarker_hits) - 1) * 7)
        add(
            biomarker_points,
            "biomarkers_exact",
            f"The source includes directly matched biomarker details: {', '.join(exact_biomarker_hits)}.",
        )
    elif gene_only_hits:
        biomarker_points = min(18, 10 + (len(gene_only_hits) - 1) * 4)
        add(
            biomarker_points,
            "biomarkers_gene",
            f"The source includes biomarker overlap at the gene level: {', '.join(gene_only_hits)}.",
        )
    elif profile_facts.biomarker_terms or profile_facts.biomarker_genes:
        cautions.append("The source did not clearly match the biomarker details that were entered.")

    if record_facts.stage_terms:
        add(8, "stage", f"The disease context also matches the entered stage or disease setting: {', '.join(record_facts.stage_terms)}.")

    if record_facts.therapy_terms:
        add(
            8,
            "therapy_context",
            f"The source references prior or current therapy context: {', '.join(record_facts.therapy_terms[:3])}.",
        )

    if record_facts.preference_terms:
        add(4, "preferences", f"It overlaps with entered preferences: {', '.join(record_facts.preference_terms[:3])}.")

    if record_facts.exclusion_terms:
        add(-14, "exclusions", f"It may conflict with entered exclusions: {', '.join(record_facts.exclusion_terms[:3])}.")
        cautions.append(f"It may conflict with entered exclusions: {', '.join(record_facts.exclusion_terms[:3])}.")

    if record.category == "clinical_trials":
        if record_facts.recruitment_bucket == "open":
            add(10, "recruitment", "The trial is listed with an open recruitment status.")
        elif record_facts.recruitment_bucket == "limited":
            add(3, "recruitment_limited", "The trial is still active, but recruitment may be limited or not currently open.")
            cautions.append("The trial is active, but the listed recruitment status may limit enrollment right now.")
        elif record_facts.recruitment_bucket == "closed":
            add(-10, "recruitment_closed", "The trial record is not currently in an open recruiting status.")
            cautions.append("The trial record is not currently in an open recruiting status.")
        else:
            cautions.append("The trial recruitment status was not clearly available.")

        if record_facts.phase_terms:
            add(2, "phase_known", f"The trial phase is stated: {', '.join(record_facts.phase_terms[:2])}.")

        if record_facts.geography_matches:
            add(
                8,
                "geography",
                f"The listed locations overlap with the entered travel area: {', '.join(record_facts.geography_matches[:4])}.",
            )
        elif record_facts.geography_terms:
            cautions.append("The listed trial locations do not clearly overlap with the entered travel area.")
        else:
            cautions.append("Trial locations were not available for a travel-feasibility review.")

    if record.category == "literature" and record_facts.has_abstract:
        add(5, "abstract_available", "The literature finding includes abstract text rather than citation-only metadata.")

    if record_facts.evidence_freshness_bucket == "very_recent":
        add(8, "freshness", "The evidence is very recent.")
    elif record_facts.evidence_freshness_bucket == "recent":
        add(5, "freshness", "The evidence is recent.")
    elif record_facts.evidence_freshness_bucket == "current":
        add(2, "freshness", "The evidence is still relatively recent.")

    if is_new:
        add(4, "novelty", "This appears to be new since the last stored version.")

    score = round(max(score, 0.0), 1)

    exact_context_hit = bool(record_facts.cancer_terms)
    strong_alignment = bool(exact_biomarker_hits or record_facts.subtype_terms or record_facts.therapy_terms)

    if score >= 78 and exact_context_hit and strong_alignment:
        relevance = "High relevance"
        confidence = "high"
    elif score >= 52 and exact_context_hit:
        relevance = "Worth reviewing"
        confidence = "medium"
    elif score >= 32 and (exact_context_hit or biomarker_hits):
        relevance = "Low confidence"
        confidence = "low"
    else:
        relevance = "Insufficient data"
        confidence = "low"

    if relevance == "Worth reviewing" and len(cautions) <= 1 and strong_alignment:
        confidence = "high"
    elif relevance == "High relevance" and len(cautions) >= 3:
        confidence = "medium"

    return MatchResult(
        score=score,
        relevance_label=relevance,
        confidence=confidence,
        why_it_surfaced=dedupe(surfaced),
        why_it_may_not_fit=dedupe(cautions),
        matching_gaps=dedupe(gaps),
        debug=debug,
        normalized_summary=record.normalized_summary or build_normalized_summary(record, record_facts),
        normalized_facts={
            "profile": profile_facts.as_dict(),
            "record": record_facts.as_dict(),
        },
    )
