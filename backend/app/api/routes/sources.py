from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.settings import SourceConfigRead, SourceConfigUpdate
from app.services.settings_service import list_source_configs, update_source_config

router = APIRouter()


@router.get("", response_model=list[SourceConfigRead])
def read_sources(db: Session = Depends(get_db)) -> list[SourceConfigRead]:
    return list_source_configs(db)


@router.put("/{source_id}", response_model=SourceConfigRead)
def update_source(source_id: int, payload: SourceConfigUpdate, db: Session = Depends(get_db)) -> SourceConfigRead:
    try:
        return update_source_config(db, source_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
