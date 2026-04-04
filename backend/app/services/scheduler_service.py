from __future__ import annotations

import logging
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = Lock()
JOB_ID = "daily-monitoring"


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None:
            _scheduler = BackgroundScheduler()
        return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")


def shutdown_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


def _run_scheduled_job() -> None:
    from app.services.monitoring_service import RunConflictError, run_monitoring

    with SessionLocal() as session:
        try:
            run_monitoring(session, triggered_by="scheduler")
        except RunConflictError:
            logger.info("Skipped scheduled run because monitoring is already in progress.")


def configure_scheduler_from_settings(daily_run_time: str) -> None:
    scheduler = get_scheduler()
    hour, minute = daily_run_time.split(":")
    scheduler.add_job(
        _run_scheduled_job,
        trigger="cron",
        id=JOB_ID,
        replace_existing=True,
        hour=int(hour),
        minute=int(minute),
        coalesce=True,
        misfire_grace_time=1800,
    )
    logger.info("Daily monitoring job scheduled for %s", daily_run_time)


def next_run_time_iso() -> str | None:
    scheduler = get_scheduler()
    job = scheduler.get_job(JOB_ID)
    if not job or not job.next_run_time:
        return None
    return job.next_run_time.isoformat()
