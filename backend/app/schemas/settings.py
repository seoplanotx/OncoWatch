from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    name: str
    connector_key: str
    enabled: bool
    settings_json: dict = Field(default_factory=dict)
    last_successful_sync_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceConfigUpdate(BaseModel):
    enabled: bool
    settings_json: dict = Field(default_factory=dict)


class AppSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    default_profile_id: int | None = None
    daily_run_time: str
    default_report_style: str
    default_report_length: str
    enabled_source_categories: list[str] = Field(default_factory=list)
    timezone_label: str
    report_output_dir: str | None = None
    demo_profile_enabled: bool
    last_health_check_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AppSettingsUpdate(BaseModel):
    default_profile_id: int | None = None
    daily_run_time: str = "08:30"
    default_report_style: str = "clinical"
    default_report_length: str = "daily_summary"
    demo_profile_enabled: bool = False


class ApiProviderConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_key: str
    display_name: str
    is_configured: bool
    api_base_url: str | None = None
    selected_model: str | None = None
    last_tested_at: datetime | None = None
    last_test_success: bool | None = None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ApiProviderConfigUpsert(BaseModel):
    provider_key: str = "openrouter"
    display_name: str = "OpenRouter"
    selected_model: str | None = None
    api_key: str | None = None


class OpenRouterTestRequest(BaseModel):
    api_key: str
    model: str | None = None


class OpenRouterTestResponse(BaseModel):
    ok: bool
    message: str
    discovered_models: list[str] = Field(default_factory=list)


class BootstrapResponse(BaseModel):
    app_name: str
    app_version: str
    disclaimer: str
    onboarding_completed: bool
    active_profile_id: int | None = None
    config_dir: str
    data_dir: str
    logs_dir: str
    reports_dir: str
    monitoring_mode: str
    privacy_summary: str
    product_scope: str
