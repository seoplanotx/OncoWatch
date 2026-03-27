from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.run import MonitoringRun
from app.schemas.run import DashboardResponse
from app.services.findings_service import build_briefing_snapshot, list_findings, rank_findings_for_briefing
from app.services.profile_service import get_active_profile
from app.services.scheduler_service import next_run_time_iso


DISCLAIMER = (
    "OncoWatch is an information monitoring and summarization tool. "
    "It does not determine treatment, trial eligibility, or medical appropriateness. "
    "All findings should be reviewed with a licensed oncology team."
)


def get_dashboard(session: Session, profile_id: int | None = None) -> DashboardResponse:
    active_profile = get_active_profile(session) if profile_id is None else None
    effective_profile_id = profile_id if profile_id is not None else (active_profile.id if active_profile else None)

    latest_run_query = select(MonitoringRun)
    if effective_profile_id is not None:
        latest_run_query = latest_run_query.where(MonitoringRun.profile_id == effective_profile_id)
    latest_run = session.scalar(latest_run_query.order_by(MonitoringRun.started_at.desc()))

    base = select(Finding)
    if effective_profile_id is not None:
        base = base.where(Finding.profile_id == effective_profile_id)

    total_findings = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    new_count = session.scalar(select(func.count()).select_from(base.where(Finding.status == "new").subquery())) or 0
    changed_count = session.scalar(select(func.count()).select_from(base.where(Finding.status == "changed").subquery())) or 0
    high_relevance = session.scalar(
        select(func.count()).select_from(base.where(Finding.relevance_label == "High relevance").subquery())
    ) or 0
    trial_matches = session.scalar(
        select(func.count()).select_from(base.where(Finding.type == "clinical_trials").subquery())
    ) or 0

    counts = {
        "total_findings": total_findings,
        "new": new_count,
        "changed": changed_count,
        "high_relevance": high_relevance,
        "trial_matches": trial_matches,
    }
    findings = list_findings(session, profile_id=effective_profile_id)
    briefing = build_briefing_snapshot(findings, latest_run=latest_run)
    recent_findings = rank_findings_for_briefing(findings)[:6]
    return DashboardResponse(
        latest_run=latest_run,
        next_scheduled_run=next_run_time_iso(),
        counts=counts,
        recent_findings=recent_findings,
        briefing=briefing,
        disclaimer=DISCLAIMER,
    )
