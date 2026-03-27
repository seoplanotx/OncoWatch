from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.connectors.base import ConnectorRecord
from app.models.finding import Finding, FindingEvidence
from app.models.run import MonitoringRun
from app.services.matching_service import MatchResult
from app.utils.dates import utcnow


STATUS_PRIORITY = {
    "new": 0,
    "changed": 1,
    "unchanged": 2,
}
RELEVANCE_PRIORITY = {
    "High relevance": 0,
    "Worth reviewing": 1,
    "Low confidence": 2,
    "Insufficient data": 3,
}
TYPE_PRIORITY = {
    "clinical_trials": 0,
    "literature": 1,
    "drug_updates": 2,
    "biomarker": 3,
}
TRIAL_RECRUITMENT_PRIORITY = {
    "open": 0,
    "limited": 1,
    "closed": 2,
}
UPDATE_TYPE_PRIORITY = {
    "literature": 0,
    "drug_updates": 1,
    "biomarker": 2,
}
FRESHNESS_PRIORITY = {
    "very_recent": 0,
    "recent": 1,
    "current": 2,
    "older": 3,
}


def _finding_hash(record: ConnectorRecord, match: MatchResult) -> str:
    payload = json.dumps(
        {
            "title": record.title,
            "source_url": record.source_url,
            "summary": record.summary,
            "location_summary": record.location_summary,
            "tags": sorted(record.tags),
            "gaps": record.gaps,
            "evidence_label": record.evidence_label,
            "evidence_snippet": record.evidence_snippet,
            "normalized_summary": match.normalized_summary,
            "normalized_facts": match.normalized_facts,
            "record_payload": record.raw_payload,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def base_query() -> Select[tuple[Finding]]:
    return select(Finding).options(selectinload(Finding.evidence_items)).order_by(Finding.updated_at.desc())


def _record_facts(finding: Finding) -> dict[str, Any]:
    match_debug = finding.match_debug if isinstance(finding.match_debug, dict) else {}
    normalized_facts = match_debug.get("normalized_facts")
    if not isinstance(normalized_facts, dict):
        return {}
    record = normalized_facts.get("record")
    return record if isinstance(record, dict) else {}


def _priority(mapping: dict[str, int], value: str | None) -> int:
    if value is None:
        return len(mapping)
    return mapping.get(str(value), len(mapping))


def _descending_datetime(value: Any) -> float:
    if value is None:
        return float("inf")
    return -float(value.timestamp())


def briefing_sort_key(finding: Finding) -> tuple[Any, ...]:
    record_facts = _record_facts(finding)
    recruitment_bucket = record_facts.get("recruitment_bucket") if finding.type == "clinical_trials" else None
    freshness_bucket = record_facts.get("evidence_freshness_bucket")

    return (
        _priority(STATUS_PRIORITY, finding.status),
        _priority(RELEVANCE_PRIORITY, finding.relevance_label),
        _priority(TRIAL_RECRUITMENT_PRIORITY, recruitment_bucket) if finding.type == "clinical_trials" else 1,
        _priority(FRESHNESS_PRIORITY, freshness_bucket),
        -round(float(finding.score or 0.0), 1),
        _priority(TYPE_PRIORITY, finding.type),
        _descending_datetime(finding.published_at),
        _descending_datetime(finding.updated_at),
        finding.title.lower(),
        finding.id,
    )


def trial_priority_key(finding: Finding) -> tuple[Any, ...]:
    record_facts = _record_facts(finding)
    return (
        _priority(TRIAL_RECRUITMENT_PRIORITY, record_facts.get("recruitment_bucket")),
        _priority(RELEVANCE_PRIORITY, finding.relevance_label),
        _priority(FRESHNESS_PRIORITY, record_facts.get("evidence_freshness_bucket")),
        -round(float(finding.score or 0.0), 1),
        _descending_datetime(finding.published_at),
        _descending_datetime(finding.updated_at),
        finding.title.lower(),
        finding.id,
    )


def literature_priority_key(finding: Finding) -> tuple[Any, ...]:
    record_facts = _record_facts(finding)
    return (
        _priority(FRESHNESS_PRIORITY, record_facts.get("evidence_freshness_bucket")),
        _priority(RELEVANCE_PRIORITY, finding.relevance_label),
        _priority(UPDATE_TYPE_PRIORITY, finding.type),
        -round(float(finding.score or 0.0), 1),
        _descending_datetime(finding.published_at),
        _descending_datetime(finding.updated_at),
        finding.title.lower(),
        finding.id,
    )


def rank_findings_for_briefing(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=briefing_sort_key)


def find_existing_finding(
    session: Session,
    *,
    profile_id: int,
    source_name: str,
    external_identifier: str,
) -> Finding | None:
    return session.scalar(
        select(Finding).where(
            Finding.profile_id == profile_id,
            Finding.source_name == source_name,
            Finding.external_identifier == external_identifier,
        )
    )


def _run_summary_ids(latest_run: MonitoringRun | None) -> tuple[set[int], set[int]]:
    if latest_run is None or not isinstance(latest_run.summary_json, dict):
        return set(), set()

    new_ids = latest_run.summary_json.get("new_finding_ids") or []
    changed_ids = latest_run.summary_json.get("changed_finding_ids") or []

    return (
        {int(item) for item in new_ids if isinstance(item, int) or str(item).isdigit()},
        {int(item) for item in changed_ids if isinstance(item, int) or str(item).isdigit()},
    )


def _section_payload(
    *,
    key: str,
    title: str,
    description: str,
    empty_message: str,
    items: list[Finding],
    total_count: int,
    limit: int,
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "description": description,
        "empty_message": empty_message,
        "count": total_count,
        "items": items[:limit],
    }


def _build_confidence_blockers(findings: list[Finding], *, limit: int = 5) -> list[dict[str, Any]]:
    blockers: dict[str, dict[str, Any]] = defaultdict(lambda: {"label": "", "finding_count": 0, "examples": []})

    for finding in findings:
        for gap in finding.matching_gaps:
            label = gap.strip()
            if not label:
                continue
            entry = blockers[label]
            entry["label"] = label
            entry["finding_count"] += 1
            if finding.title not in entry["examples"] and len(entry["examples"]) < 3:
                entry["examples"].append(finding.title)

    return sorted(
        blockers.values(),
        key=lambda item: (-int(item["finding_count"]), str(item["label"]).lower()),
    )[:limit]


def build_briefing_snapshot(
    findings: list[Finding],
    *,
    latest_run: MonitoringRun | None = None,
    section_limit: int = 4,
    blocker_limit: int = 5,
) -> dict[str, Any]:
    ranked = rank_findings_for_briefing(findings)
    new_ids, changed_ids = _run_summary_ids(latest_run)

    if new_ids or changed_ids:
        new_items = [finding for finding in ranked if finding.id in new_ids]
        changed_items = [finding for finding in ranked if finding.id in changed_ids]
    elif latest_run is not None:
        new_items = [finding for finding in ranked if finding.monitoring_run_id == latest_run.id and finding.status == "new"]
        changed_items = [
            finding for finding in ranked if finding.monitoring_run_id == latest_run.id and finding.status == "changed"
        ]
    else:
        new_items = [finding for finding in ranked if finding.status == "new"]
        changed_items = [finding for finding in ranked if finding.status == "changed"]

    used_ids: set[int] = set()
    new_section_items = new_items[:section_limit]
    used_ids.update(item.id for item in new_section_items)

    changed_section_items = [item for item in changed_items if item.id not in used_ids][:section_limit]
    used_ids.update(item.id for item in changed_section_items)

    trial_candidates = [item for item in ranked if item.type == "clinical_trials" and item.id not in used_ids]
    trial_items = sorted(trial_candidates, key=trial_priority_key)[:section_limit]
    used_ids.update(item.id for item in trial_items)

    update_candidates = [
        item for item in ranked if item.type in {"literature", "drug_updates", "biomarker"} and item.id not in used_ids
    ]
    update_items = sorted(update_candidates, key=literature_priority_key)[:section_limit]

    focus_for_blockers = [*new_section_items, *changed_section_items, *trial_items, *update_items] or ranked[:8]
    blockers = _build_confidence_blockers(focus_for_blockers, limit=blocker_limit)

    return {
        "latest_run_started_at": latest_run.started_at if latest_run else None,
        "latest_run_completed_at": latest_run.completed_at if latest_run else None,
        "new_count": latest_run.new_findings_count if latest_run else len(new_items),
        "changed_count": latest_run.changed_findings_count if latest_run else len(changed_items),
        "sections": [
            _section_payload(
                key="new_findings",
                title="New findings",
                description="Items first seen in the latest monitoring cycle.",
                empty_message="No new findings were detected in the latest run.",
                items=new_items,
                total_count=latest_run.new_findings_count if latest_run else len(new_items),
                limit=section_limit,
            ),
            _section_payload(
                key="changed_findings",
                title="Changed findings",
                description="Previously seen items with meaningful source-backed changes.",
                empty_message="No previously stored findings changed in the latest run.",
                items=changed_items,
                total_count=latest_run.changed_findings_count if latest_run else len(changed_items),
                limit=section_limit,
            ),
            _section_payload(
                key="top_trial_matches",
                title="Top trial matches",
                description="Open, higher-signal trial records prioritized for quick review.",
                empty_message="No trial matches are stored for this profile yet.",
                items=sorted(trial_candidates, key=trial_priority_key),
                total_count=len(trial_candidates),
                limit=section_limit,
            ),
            _section_payload(
                key="top_literature_updates",
                title="Top literature updates",
                description="Fresh literature, drug, and biomarker updates prioritized for scanability.",
                empty_message="No literature or update findings are stored for this profile yet.",
                items=sorted(update_candidates, key=literature_priority_key),
                total_count=len(update_candidates),
                limit=section_limit,
            ),
        ],
        "blockers": blockers,
    }


def list_findings(
    session: Session,
    *,
    profile_id: int | None = None,
    finding_type: str | None = None,
    q: str | None = None,
) -> list[Finding]:
    query = base_query()
    if profile_id is not None:
        query = query.where(Finding.profile_id == profile_id)
    if finding_type:
        query = query.where(Finding.type == finding_type)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            func.lower(Finding.title).like(like) | func.lower(Finding.normalized_summary).like(like)
        )
    return rank_findings_for_briefing(session.scalars(query).all())


def get_finding(session: Session, finding_id: int) -> Finding | None:
    return session.scalar(base_query().where(Finding.id == finding_id))


def upsert_finding(
    session: Session,
    *,
    profile_id: int,
    monitoring_run_id: int | None,
    record: ConnectorRecord,
    match: MatchResult,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    llm_metadata: dict | None = None,
) -> tuple[Finding, str]:
    content_hash = _finding_hash(record, match)
    finding = find_existing_finding(
        session,
        profile_id=profile_id,
        source_name=record.source_name,
        external_identifier=record.external_identifier,
    )
    state = "unchanged"
    if finding is None:
        finding = Finding(
            profile_id=profile_id,
            monitoring_run_id=monitoring_run_id,
            type=record.category,
            title=record.title,
            source_name=record.source_name,
            source_url=record.source_url,
            external_identifier=record.external_identifier,
            retrieved_at=utcnow(),
            published_at=record.published_at,
            structured_tags=record.tags,
            raw_summary=record.summary,
            normalized_summary=match.normalized_summary or record.normalized_summary or record.summary,
            why_it_surfaced="\n".join(match.why_it_surfaced),
            why_it_may_not_fit="\n".join(match.why_it_may_not_fit),
            confidence=match.confidence,
            score=match.score,
            relevance_label=match.relevance_label,
            status="new",
            location_summary=record.location_summary,
            matching_gaps=match.matching_gaps,
            match_debug={
                **match.debug,
                "normalized_facts": match.normalized_facts,
            },
            content_hash=content_hash,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_metadata=llm_metadata or {},
        )
        session.add(finding)
        session.flush()
        state = "new"
    else:
        finding.monitoring_run_id = monitoring_run_id
        finding.retrieved_at = utcnow()
        finding.published_at = record.published_at
        finding.title = record.title
        finding.source_url = record.source_url
        finding.structured_tags = record.tags
        finding.raw_summary = record.summary
        finding.normalized_summary = match.normalized_summary or record.normalized_summary or record.summary
        finding.why_it_surfaced = "\n".join(match.why_it_surfaced)
        finding.why_it_may_not_fit = "\n".join(match.why_it_may_not_fit)
        finding.confidence = match.confidence
        finding.score = match.score
        finding.relevance_label = match.relevance_label
        finding.location_summary = record.location_summary
        finding.matching_gaps = match.matching_gaps
        finding.match_debug = {
            **match.debug,
            "normalized_facts": match.normalized_facts,
        }
        finding.llm_provider = llm_provider
        finding.llm_model = llm_model
        finding.llm_metadata = llm_metadata or {}
        if finding.content_hash != content_hash:
            finding.status = "changed"
            finding.content_hash = content_hash
            state = "changed"
        else:
            finding.status = "unchanged"

    finding.evidence_items.clear()
    finding.evidence_items.append(
        FindingEvidence(
            label=record.evidence_label,
            snippet=record.evidence_snippet or record.summary,
            source_url=record.source_url,
            source_identifier=record.external_identifier,
            published_at=record.published_at,
        )
    )
    session.flush()
    return finding, state
