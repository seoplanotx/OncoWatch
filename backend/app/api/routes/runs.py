from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.run import MonitoringRun
from app.schemas.run import MonitoringRunRead, TriggerRunRequest
from app.services.monitoring_service import RunConflictError, run_monitoring

router = APIRouter()


@router.get("", response_model=list[MonitoringRunRead])
def list_runs(db: Session = Depends(get_db)) -> list[MonitoringRunRead]:
    return db.scalars(select(MonitoringRun).order_by(MonitoringRun.started_at.desc())).all()


@router.post("/trigger", response_model=MonitoringRunRead)
def trigger_run(payload: TriggerRunRequest, db: Session = Depends(get_db)) -> MonitoringRunRead:
    try:
        return run_monitoring(db, profile_id=payload.profile_id, triggered_by=payload.triggered_by)
    except RunConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
