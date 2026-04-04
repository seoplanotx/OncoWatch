from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.paths import get_app_paths
from app.core.release import APP_NAME, APP_VERSION, MONITORING_MODE, PRIVACY_SUMMARY, PRODUCT_SCOPE
from app.models.settings import OnboardingState
from app.schemas.settings import BootstrapResponse
from app.services.bootstrap_service import DISCLAIMER_TEXT
from app.services.profile_service import get_active_profile

router = APIRouter()


@router.get("", response_model=BootstrapResponse)
def get_bootstrap(db: Session = Depends(get_db)) -> BootstrapResponse:
    paths = get_app_paths()
    profile = get_active_profile(db)
    onboarding = db.scalar(select(OnboardingState))
    return BootstrapResponse(
        app_name=APP_NAME,
        app_version=APP_VERSION,
        disclaimer=DISCLAIMER_TEXT,
        onboarding_completed=bool(onboarding.is_completed) if onboarding else False,
        active_profile_id=profile.id if profile else None,
        config_dir=str(paths.config_dir),
        data_dir=str(paths.data_dir),
        logs_dir=str(paths.logs_dir),
        reports_dir=str(paths.reports_dir),
        monitoring_mode=MONITORING_MODE,
        privacy_summary=PRIVACY_SUMMARY,
        product_scope=PRODUCT_SCOPE,
    )
