from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.settings import (
    ApiProviderConfigRead,
    ApiProviderConfigUpsert,
    AppSettingsRead,
    AppSettingsUpdate,
    OpenRouterTestRequest,
    OpenRouterTestResponse,
)
from app.services.settings_service import (
    get_provider_config,
    get_settings,
    list_openrouter_models,
    save_provider_config,
    test_openrouter,
    update_settings,
)

router = APIRouter()


@router.get("", response_model=AppSettingsRead)
def read_settings(db: Session = Depends(get_db)) -> AppSettingsRead:
    return get_settings(db)


@router.put("", response_model=AppSettingsRead)
def write_settings(payload: AppSettingsUpdate, db: Session = Depends(get_db)) -> AppSettingsRead:
    return update_settings(db, payload)


@router.get("/provider/openrouter", response_model=ApiProviderConfigRead | None)
def read_openrouter_config(db: Session = Depends(get_db)) -> ApiProviderConfigRead | None:
    return get_provider_config(db, "openrouter")


@router.post("/provider/openrouter/save", response_model=ApiProviderConfigRead)
def save_openrouter_config(payload: ApiProviderConfigUpsert, db: Session = Depends(get_db)) -> ApiProviderConfigRead:
    return save_provider_config(db, payload)


@router.post("/provider/openrouter/test", response_model=OpenRouterTestResponse)
def test_openrouter_key(payload: OpenRouterTestRequest, db: Session = Depends(get_db)) -> OpenRouterTestResponse:
    return test_openrouter(db, payload.api_key, payload.model)


@router.get("/provider/openrouter/models", response_model=list[str])
def get_openrouter_models(db: Session = Depends(get_db)) -> list[str]:
    return list_openrouter_models(db)
