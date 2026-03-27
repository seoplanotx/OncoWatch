from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.run import MonitoringRun
from app.schemas.run import DashboardResponse
from app.services.findings_service import list_findings
from app.services.scheduler_service import next_run_time_iso


DISCLAIMER = (
    "OncoWatch is an information monitoring and summarization tool. "
    "It does not determine treatment, trial eligibility, or medical appropriateness. "
    "All findings should be reviewed with a licensed oncology team."
)


def get_dashboard(session: Session, profile_id: int | None = None) -> DashboardResponse:
    latest_run = session.scalar(select(MonitoringRun).order_by(MonitoringRun.started_at.desc()))

    base = select(Finding)
    if profile_id is not None:
        base = base.where(Finding.profile_id == profile_id)

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
    recent_findings = list_findings(session, profile_id=profile_id)[:6]
    return DashboardResponse(
        latest_run=latest_run,
        next_scheduled_run=next_run_time_iso(),
        counts=counts,
        recent_findings=recent_findings,
        disclaimer=DISCLAIMER,
    )
