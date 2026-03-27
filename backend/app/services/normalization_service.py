from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from app.connectors.base import ConnectorRecord
from app.utils.dates import utcnow


DISEASE_SYNONYMS = {
    "non small cell lung cancer": ["nsclc", "lung cancer"],
    "small cell lung cancer": ["sclc"],
    "triple negative breast cancer": ["tnbc"],
    "hormone receptor positive breast cancer": ["hr positive breast cancer", "hr+ breast cancer"],
}

SUBTYPE_SYNONYMS = {
    "adenocarcinoma": ["adeno"],
}

US_STATE_CODES = {
    "alabama": "al",
    "alaska": "ak",
    "arizona": "az",
    "arkansas": "ar",
    "california": "ca",
    "colorado": "co",
    "connecticut": "ct",
    "delaware": "de",
    "district of columbia": "dc",
    "florida": "fl",
    "georgia": "ga",
    "hawaii": "hi",
    "idaho": "id",
    "illinois": "il",
    "indiana": "in",
    "iowa": "ia",
    "kansas": "ks",
    "kentucky": "ky",
    "louisiana": "la",
    "maine": "me",
    "maryland": "md",
    "massachusetts": "ma",
    "michigan": "mi",
    "minnesota": "mn",
    "mississippi": "ms",
    "missouri": "mo",
    "montana": "mt",
    "nebraska": "ne",
    "nevada": "nv",
    "new hampshire": "nh",
    "new jersey": "nj",
    "new mexico": "nm",
    "new york": "ny",
    "north carolina": "nc",
    "north dakota": "nd",
    "ohio": "oh",
    "oklahoma": "ok",
    "oregon": "or",
    "pennsylvania": "pa",
    "rhode island": "ri",
    "south carolina": "sc",
    "south dakota": "sd",
    "tennessee": "tn",
    "texas": "tx",
    "utah": "ut",
    "vermont": "vt",
    "virginia": "va",
    "washington": "wa",
    "west virginia": "wv",
    "wisconsin": "wi",
    "wyoming": "wy",
}
US_STATE_NAMES = {code: name for name, code in US_STATE_CODES.items()}

OPEN_RECRUITMENT_STATUSES = {"recruiting", "not yet recruiting", "enrolling by invitation"}
LIMITED_RECRUITMENT_STATUSES = {"active not recruiting", "suspended", "temporarily not available"}
CLOSED_RECRUITMENT_STATUSES = {
    "completed",
    "withdrawn",
    "terminated",
    "unknown status",
    "no longer available",
    "approved for marketing",
}


@dataclass(slots=True)
class NormalizedProfileFacts:
    cancer_terms: list[str] = field(default_factory=list)
    subtype_terms: list[str] = field(default_factory=list)
    stage_terms: list[str] = field(default_factory=list)
    biomarker_terms: list[str] = field(default_factory=list)
    biomarker_genes: list[str] = field(default_factory=list)
    therapy_terms: list[str] = field(default_factory=list)
    preference_terms: list[str] = field(default_factory=list)
    exclusion_terms: list[str] = field(default_factory=list)
    geography_terms: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NormalizedRecordFacts:
    source_type: str
    cancer_terms: list[str] = field(default_factory=list)
    subtype_terms: list[str] = field(default_factory=list)
    stage_terms: list[str] = field(default_factory=list)
    biomarker_terms: list[str] = field(default_factory=list)
    biomarker_genes: list[str] = field(default_factory=list)
    therapy_terms: list[str] = field(default_factory=list)
    preference_terms: list[str] = field(default_factory=list)
    exclusion_terms: list[str] = field(default_factory=list)
    condition_terms: list[str] = field(default_factory=list)
    intervention_terms: list[str] = field(default_factory=list)
    recruitment_status: str | None = None
    recruitment_bucket: str | None = None
    phase_terms: list[str] = field(default_factory=list)
    geography_terms: list[str] = field(default_factory=list)
    geography_matches: list[str] = field(default_factory=list)
    evidence_freshness_days: int | None = None
    evidence_freshness_bucket: str | None = None
    has_abstract: bool = False
    source_identifiers: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower().replace("/", " ").replace("-", " ")
    return " ".join(lowered.split())


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        item = normalize_text(value)
        if not item or item in seen:
            continue
        seen.add(item)
        deduped.append(value)
    return deduped


def normalize_profile(profile: Any) -> NormalizedProfileFacts:
    cancer_terms = _expand_disease_terms(getattr(profile, "cancer_type", None))
    subtype_terms = _expand_subtype_terms(getattr(profile, "subtype", None))
    stage_terms = _expand_simple_terms(getattr(profile, "stage_or_context", None))

    biomarker_terms: list[str] = []
    biomarker_genes: list[str] = []
    for biomarker in getattr(profile, "biomarkers", []):
        gene = normalize_text(getattr(biomarker, "name", None))
        variant = normalize_text(getattr(biomarker, "variant", None))
        if gene:
            biomarker_genes.append(gene)
            biomarker_terms.append(gene)
        if gene and variant:
            biomarker_terms.append(f"{gene} {variant}")

    therapy_terms: list[str] = []
    for therapy in getattr(profile, "therapy_history", []):
        therapy_terms.extend(_expand_simple_terms(getattr(therapy, "therapy_name", None)))
        therapy_terms.extend(_expand_simple_terms(getattr(therapy, "therapy_type", None)))

    return NormalizedProfileFacts(
        cancer_terms=dedupe(cancer_terms),
        subtype_terms=dedupe(subtype_terms),
        stage_terms=dedupe(stage_terms),
        biomarker_terms=dedupe(biomarker_terms),
        biomarker_genes=dedupe(biomarker_genes),
        therapy_terms=dedupe(therapy_terms),
        preference_terms=dedupe(_expand_list_terms(getattr(profile, "would_consider", []) or [])),
        exclusion_terms=dedupe(_expand_list_terms(getattr(profile, "would_not_consider", []) or [])),
        geography_terms=dedupe(_expand_geography_terms(getattr(profile, "location_label", None))),
    )


def normalize_record(record: ConnectorRecord, profile_facts: NormalizedProfileFacts) -> NormalizedRecordFacts:
    payload = record.raw_payload or {}
    source_texts = _collect_source_texts(record, payload)
    normalized_source_texts = [normalize_text(item) for item in source_texts if normalize_text(item)]

    condition_terms = dedupe(payload.get("conditions", []) or [])
    intervention_terms = dedupe(payload.get("interventions", []) or [])
    phase_terms = dedupe(payload.get("phases", []) or [])

    recruitment_status = normalize_text(payload.get("recruitment_status"))
    if not recruitment_status:
        recruitment_status = _infer_recruitment_status(normalized_source_texts)

    geography_terms = dedupe(_expand_list_terms(payload.get("locations", []) or []))
    if record.location_summary:
        geography_terms = dedupe([*geography_terms, *(_expand_geography_terms(record.location_summary))])

    geography_matches = [term for term in geography_terms if term in set(profile_facts.geography_terms)]
    missing_fields = list(record.gaps)
    has_abstract = bool(payload.get("abstract_sections") or payload.get("abstract_text"))

    if record.category == "clinical_trials":
        if not recruitment_status:
            missing_fields.append("Recruitment status was not available in the trial record.")
        if not phase_terms:
            missing_fields.append("Trial phase was not available in the trial record.")
        if not geography_terms:
            missing_fields.append("Study locations were not available in the trial record.")
    if record.category == "literature" and not has_abstract:
        missing_fields.append("Abstract text was not available from PubMed for this citation.")

    freshness_days = None
    freshness_bucket = None
    if record.published_at is not None:
        freshness_days = max((utcnow() - record.published_at).days, 0)
        if freshness_days <= 30:
            freshness_bucket = "very_recent"
        elif freshness_days <= 120:
            freshness_bucket = "recent"
        elif freshness_days <= 365:
            freshness_bucket = "current"
        else:
            freshness_bucket = "older"

    source_identifiers = [record.external_identifier]
    identifiers = payload.get("identifiers")
    if isinstance(identifiers, dict):
        source_identifiers.extend(str(value) for value in identifiers.values() if value)

    return NormalizedRecordFacts(
        source_type=record.category,
        cancer_terms=_present_terms(profile_facts.cancer_terms, normalized_source_texts),
        subtype_terms=_present_terms(profile_facts.subtype_terms, normalized_source_texts),
        stage_terms=_present_terms(profile_facts.stage_terms, normalized_source_texts),
        biomarker_terms=_present_terms(profile_facts.biomarker_terms, normalized_source_texts),
        biomarker_genes=_present_terms(profile_facts.biomarker_genes, normalized_source_texts),
        therapy_terms=_present_terms(profile_facts.therapy_terms, normalized_source_texts),
        preference_terms=_present_terms(profile_facts.preference_terms, normalized_source_texts),
        exclusion_terms=_present_terms(profile_facts.exclusion_terms, normalized_source_texts),
        condition_terms=condition_terms,
        intervention_terms=intervention_terms,
        recruitment_status=recruitment_status or None,
        recruitment_bucket=_bucket_recruitment_status(recruitment_status),
        phase_terms=phase_terms,
        geography_terms=geography_terms,
        geography_matches=dedupe(geography_matches),
        evidence_freshness_days=freshness_days,
        evidence_freshness_bucket=freshness_bucket,
        has_abstract=has_abstract,
        source_identifiers=dedupe(source_identifiers),
        missing_fields=dedupe(missing_fields),
    )


def build_normalized_summary(record: ConnectorRecord, facts: NormalizedRecordFacts) -> str:
    payload = record.raw_payload or {}
    if record.category == "clinical_trials":
        parts: list[str] = []
        if facts.recruitment_status:
            parts.append(_display_text(facts.recruitment_status))
        if facts.phase_terms:
            parts.append(", ".join(_display_text(phase) for phase in facts.phase_terms))
        if payload.get("conditions"):
            parts.append(f"Conditions: {', '.join(payload['conditions'][:3])}")
        if payload.get("interventions"):
            parts.append(f"Interventions: {', '.join(payload['interventions'][:3])}")
        if payload.get("sponsor"):
            parts.append(f"Sponsor: {payload['sponsor']}")
        if payload.get("locations"):
            parts.append(f"Sites: {', '.join(payload['locations'][:3])}")
        if record.evidence_snippet:
            parts.append(record.evidence_snippet)
        return ". ".join(part.rstrip(".") for part in parts if part).strip() + "."

    if record.category == "literature":
        parts = []
        if payload.get("journal"):
            parts.append(f"Journal: {payload['journal']}")
        authors = payload.get("authors") or []
        if authors:
            parts.append(f"Authors: {', '.join(authors[:3])}")
        if record.evidence_snippet:
            parts.append(record.evidence_snippet)
        if not parts:
            parts.append(record.summary)
        return ". ".join(part.rstrip(".") for part in parts if part).strip() + "."

    return record.summary


def _collect_source_texts(record: ConnectorRecord, payload: dict[str, Any]) -> list[str]:
    values: list[str] = [
        record.title,
        record.summary,
        record.location_summary or "",
        record.evidence_snippet or "",
        payload.get("brief_summary") or "",
        payload.get("detailed_description_excerpt") or "",
        payload.get("eligibility_criteria_excerpt") or "",
        payload.get("inclusion_excerpt") or "",
        payload.get("exclusion_excerpt") or "",
        payload.get("abstract_text") or "",
        payload.get("journal") or "",
        payload.get("sponsor") or "",
    ]

    for key in ("conditions", "interventions", "keywords", "locations", "phases", "mesh_terms"):
        values.extend(str(item) for item in payload.get(key, []) or [])

    for abstract_section in payload.get("abstract_sections", []) or []:
        values.append(str(abstract_section))

    authors = payload.get("authors") or []
    values.extend(str(author) for author in authors)
    return [value for value in values if isinstance(value, str) and value.strip()]


def _expand_disease_terms(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []
    terms = [normalized]
    terms.extend(DISEASE_SYNONYMS.get(normalized, []))

    tokens = normalized.split()
    if len(tokens) >= 2 and tokens[-1] in {"cancer", "carcinoma", "sarcoma", "lymphoma", "leukemia", "melanoma"}:
        terms.append(" ".join(tokens[-2:]))
    return dedupe(terms)


def _expand_subtype_terms(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []
    return dedupe([normalized, *SUBTYPE_SYNONYMS.get(normalized, [])])


def _expand_simple_terms(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []
    return [normalized]


def _expand_list_terms(values: Iterable[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = normalize_text(value)
        if normalized:
            terms.append(normalized)
    return dedupe(terms)


def _expand_geography_terms(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []

    parts = [normalized]
    tokens = normalized.replace(",", " ").split()
    for token in tokens:
        if len(token) > 1:
            parts.append(token)
        if token in US_STATE_NAMES:
            parts.append(US_STATE_NAMES[token])
        if token in US_STATE_CODES:
            parts.append(US_STATE_CODES[token])
    if "united states" in normalized:
        parts.extend(["united states", "usa", "us"])
    return dedupe(parts)


def _present_terms(candidates: list[str], source_texts: list[str]) -> list[str]:
    matches: list[str] = []
    haystack = " ".join(source_texts)
    for candidate in candidates:
        if candidate and candidate in haystack:
            matches.append(candidate)
    return dedupe(matches)


def _infer_recruitment_status(source_texts: list[str]) -> str | None:
    haystack = " ".join(source_texts)
    for status in [*OPEN_RECRUITMENT_STATUSES, *LIMITED_RECRUITMENT_STATUSES, *CLOSED_RECRUITMENT_STATUSES]:
        if status in haystack:
            return status
    return None


def _bucket_recruitment_status(status: str | None) -> str | None:
    if not status:
        return None
    if status in OPEN_RECRUITMENT_STATUSES:
        return "open"
    if status in LIMITED_RECRUITMENT_STATUSES:
        return "limited"
    if status in CLOSED_RECRUITMENT_STATUSES:
        return "closed"
    return "unknown"


def _display_text(value: str) -> str:
    return value.replace("_", " ").title()
