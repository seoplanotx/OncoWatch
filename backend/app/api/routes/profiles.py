from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.profile import PatientProfileCreate, PatientProfileRead, PatientProfileUpdate
from app.services.profile_service import create_profile, get_active_profile, get_profile, list_profiles, update_profile

router = APIRouter()


@router.get("", response_model=list[PatientProfileRead])
def get_profiles(db: Session = Depends(get_db)) -> list[PatientProfileRead]:
    return list_profiles(db)


@router.get("/active", response_model=PatientProfileRead | None)
def get_current_profile(db: Session = Depends(get_db)) -> PatientProfileRead | None:
    return get_active_profile(db)


@router.get("/{profile_id}", response_model=PatientProfileRead)
def get_profile_detail(profile_id: int, db: Session = Depends(get_db)) -> PatientProfileRead:
    profile = get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("", response_model=PatientProfileRead)
def create_profile_route(payload: PatientProfileCreate, db: Session = Depends(get_db)) -> PatientProfileRead:
    return create_profile(db, payload)


@router.put("/{profile_id}", response_model=PatientProfileRead)
def update_profile_route(profile_id: int, payload: PatientProfileUpdate, db: Session = Depends(get_db)) -> PatientProfileRead:
    try:
        return update_profile(db, profile_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
