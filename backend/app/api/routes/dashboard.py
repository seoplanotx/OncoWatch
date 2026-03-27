from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.run import DashboardResponse
from app.services.dashboard_service import get_dashboard

router = APIRouter()


@router.get("", response_model=DashboardResponse)
def read_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return get_dashboard(db)
