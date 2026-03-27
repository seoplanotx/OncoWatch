from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.health import HealthCheckResponse
from app.services.health_service import run_health_check

router = APIRouter()


@router.get("", response_model=HealthCheckResponse)
def health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    return run_health_check(db)
