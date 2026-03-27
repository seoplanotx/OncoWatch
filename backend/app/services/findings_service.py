from __future__ import annotations

import hashlib

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.connectors.base import ConnectorRecord
from app.models.finding import Finding, FindingEvidence
from app.services.matching_service import MatchResult
from app.utils.dates import utcnow


def _finding_hash(record: ConnectorRecord) -> str:
    payload = "|".join(
        [
            record.title,
            record.source_url,
            record.summary,
            record.location_summary or "",
            ",".join(sorted(record.tags)),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def base_query() -> Select[tuple[Finding]]:
    return select(Finding).options(selectinload(Finding.evidence_items)).order_by(Finding.updated_at.desc())


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
    return session.scalars(query).all()


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
    content_hash = _finding_hash(record)
    finding = session.scalar(
        select(Finding).where(
            Finding.profile_id == profile_id,
            Finding.source_name == record.source_name,
            Finding.external_identifier == record.external_identifier,
        )
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
            normalized_summary=record.summary,
            why_it_surfaced="\n".join(match.why_it_surfaced),
            why_it_may_not_fit="\n".join(match.why_it_may_not_fit),
            confidence=match.confidence,
            score=match.score,
            relevance_label=match.relevance_label,
            status="new",
            location_summary=record.location_summary,
            matching_gaps=match.matching_gaps,
            match_debug=match.debug,
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
        finding.normalized_summary = record.summary
        finding.why_it_surfaced = "\n".join(match.why_it_surfaced)
        finding.why_it_may_not_fit = "\n".join(match.why_it_may_not_fit)
        finding.confidence = match.confidence
        finding.score = match.score
        finding.relevance_label = match.relevance_label
        finding.location_summary = record.location_summary
        finding.matching_gaps = match.matching_gaps
        finding.match_debug = match.debug
        finding.llm_provider = llm_provider
        finding.llm_model = llm_model
        finding.llm_metadata = llm_metadata or {}
        if finding.content_hash != content_hash:
            finding.status = "changed"
            finding.content_hash = content_hash
            state = "changed"

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
