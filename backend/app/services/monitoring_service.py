from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.connectors.base import ConnectorContext
from app.connectors.registry import connector_registry
from app.models.run import MonitoringRun
from app.models.settings import SourceConfig
from app.services.findings_service import upsert_finding
from app.services.matching_service import evaluate
from app.services.profile_service import get_active_profile, get_profile
from app.utils.dates import utcnow

logger = logging.getLogger(__name__)


def run_monitoring(session: Session, profile_id: int | None = None, triggered_by: str = "manual") -> MonitoringRun:
    profile = get_profile(session, profile_id) if profile_id else get_active_profile(session)
    run = MonitoringRun(
        profile_id=profile.id if profile else None,
        status="running",
        triggered_by=triggered_by,
        started_at=utcnow(),
        summary_json={"connectors": []},
        sources_checked=[],
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    if profile is None:
        run.status = "failed"
        run.error_text = "No patient profile is available yet."
        run.completed_at = utcnow()
        session.commit()
        return run

    registry = connector_registry()
    source_configs = session.query(SourceConfig).filter(SourceConfig.enabled.is_(True)).all()

    new_count = 0
    changed_count = 0
    connector_summaries: list[dict] = []

    for source in source_configs:
        connector = registry.get(source.connector_key)
        if connector is None:
            connector_summaries.append(
                {"connector_key": source.connector_key, "status": "missing", "retrieved": 0}
            )
            continue

        context = ConnectorContext(profile=profile, source_config=source, requested_at=utcnow())
        try:
            records = connector.fetch(context)
            run.sources_checked = [*run.sources_checked, source.connector_key]
            source.last_successful_sync_at = utcnow()
            source.last_error = None
            for record in records:
                match = evaluate(profile, record, is_new=True)
                _, state = upsert_finding(
                    session,
                    profile_id=profile.id,
                    monitoring_run_id=run.id,
                    record=record,
                    match=match,
                )
                if state == "new":
                    new_count += 1
                elif state == "changed":
                    changed_count += 1

            connector_summaries.append(
                {
                    "connector_key": source.connector_key,
                    "status": "ok",
                    "retrieved": len(records),
                }
            )
        except Exception as exc:
            logger.exception("Connector failed: %s", source.connector_key)
            source.last_error = str(exc)
            connector_summaries.append(
                {
                    "connector_key": source.connector_key,
                    "status": "error",
                    "retrieved": 0,
                    "error": str(exc),
                }
            )

    run.new_findings_count = new_count
    run.changed_findings_count = changed_count
    run.completed_at = utcnow()
    run.summary_json = {"connectors": connector_summaries}
    run.status = "completed"
    session.commit()
    session.refresh(run)
    return run
