from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.settings import OnboardingState
from app.schemas.onboarding import DemoProfileResponse, OnboardingCompleteRequest, OnboardingStateRead
from app.services.health_service import run_health_check
from app.services.profile_service import create_demo_profile
from app.utils.dates import utcnow

router = APIRouter()


@router.get("/state", response_model=OnboardingStateRead)
def get_state(db: Session = Depends(get_db)) -> OnboardingStateRead:
    state = db.scalar(select(OnboardingState))
    if state is None:
        state = OnboardingState(is_completed=False, current_step="welcome", show_demo_profile_option=True)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


@router.post("/complete", response_model=OnboardingStateRead)
def complete_onboarding(payload: OnboardingCompleteRequest, db: Session = Depends(get_db)) -> OnboardingStateRead:
    state = db.scalar(select(OnboardingState))
    if state is None:
        state = OnboardingState()
        db.add(state)

    health = run_health_check(db)
    state.last_health_check = health.model_dump(mode="json")
    if payload.is_completed and not health.overall_ok:
        state.is_completed = False
        state.current_step = "health_check"
        state.completed_at = None
        db.commit()
        raise HTTPException(status_code=409, detail="Resolve blocking health check failures before finishing setup.")

    state.welcome_acknowledged = payload.welcome_acknowledged
    state.current_step = payload.current_step or "completed"
    state.is_completed = payload.is_completed
    state.completed_at = utcnow() if payload.is_completed else None
    db.commit()
    db.refresh(state)
    return state


@router.post("/demo-profile", response_model=DemoProfileResponse)
def create_onboarding_demo_profile(db: Session = Depends(get_db)) -> DemoProfileResponse:
    profile = create_demo_profile(db)
    return DemoProfileResponse(profile_id=profile.id)
