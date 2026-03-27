from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret
from app.models.settings import ApiProviderConfig, AppSettings, SourceConfig
from app.schemas.settings import AppSettingsUpdate, ApiProviderConfigUpsert, OpenRouterTestResponse, SourceConfigUpdate
from app.services.llm_service import OpenRouterClient
from app.services.scheduler_service import configure_scheduler_from_settings


FALLBACK_MODELS = [
    "openai/gpt-4.1-mini",
    "anthropic/claude-3.7-sonnet",
    "google/gemini-2.5-pro",
    "meta-llama/llama-4-maverick",
]


def get_settings(session: Session) -> AppSettings:
    settings = session.scalar(select(AppSettings))
    if settings is None:
        settings = AppSettings(
            daily_run_time="08:30",
            default_report_style="clinical",
            default_report_length="daily_summary",
            enabled_source_categories=["clinical_trials", "literature", "drug_updates", "biomarker"],
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def update_settings(session: Session, payload: AppSettingsUpdate) -> AppSettings:
    settings = get_settings(session)
    settings.default_profile_id = payload.default_profile_id
    settings.daily_run_time = payload.daily_run_time
    settings.default_report_style = payload.default_report_style
    settings.default_report_length = payload.default_report_length
    settings.demo_profile_enabled = payload.demo_profile_enabled
    settings.last_health_check_at = datetime.now(timezone.utc)
    session.commit()
    configure_scheduler_from_settings(settings.daily_run_time)
    return get_settings(session)


def list_source_configs(session: Session) -> list[SourceConfig]:
    return session.scalars(select(SourceConfig).order_by(SourceConfig.category, SourceConfig.name)).all()


def update_source_config(session: Session, source_id: int, payload: SourceConfigUpdate) -> SourceConfig:
    source = session.get(SourceConfig, source_id)
    if source is None:
        raise ValueError("Source config not found")
    source.enabled = payload.enabled
    source.settings_json = payload.settings_json
    session.commit()

    settings = get_settings(session)
    enabled_categories = sorted({config.category for config in list_source_configs(session) if config.enabled})
    settings.enabled_source_categories = enabled_categories
    session.commit()
    return source


def get_provider_config(session: Session, provider_key: str = "openrouter") -> ApiProviderConfig | None:
    return session.scalar(select(ApiProviderConfig).where(ApiProviderConfig.provider_key == provider_key))


def save_provider_config(session: Session, payload: ApiProviderConfigUpsert) -> ApiProviderConfig:
    provider = get_provider_config(session, payload.provider_key)
    if provider is None:
        provider = ApiProviderConfig(provider_key=payload.provider_key, display_name=payload.display_name)
        session.add(provider)

    provider.display_name = payload.display_name
    provider.selected_model = payload.selected_model
    if payload.api_key is not None and payload.api_key.strip():
        provider.encrypted_api_key = encrypt_secret(payload.api_key.strip())
        provider.is_configured = True
    provider.last_tested_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(provider)
    return provider


def get_provider_api_key(provider: ApiProviderConfig | None) -> str | None:
    if provider is None:
        return None
    return decrypt_secret(provider.encrypted_api_key)


def test_openrouter(session: Session, api_key: str, model: str | None = None) -> OpenRouterTestResponse:
    client = OpenRouterClient(api_key=api_key)
    ok, message, models = client.test_api_key()
    return OpenRouterTestResponse(ok=ok, message=message, discovered_models=models[:20])


def list_openrouter_models(session: Session, api_key: str | None = None) -> list[str]:
    if api_key:
        client = OpenRouterClient(api_key=api_key)
        ok, _, models = client.test_api_key()
        if ok and models:
            return models
    provider = get_provider_config(session)
    stored_key = get_provider_api_key(provider)
    if stored_key:
        client = OpenRouterClient(api_key=stored_key)
        ok, _, models = client.test_api_key()
        if ok and models:
            return models
    return FALLBACK_MODELS
