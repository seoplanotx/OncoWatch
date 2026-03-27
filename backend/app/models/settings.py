from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.utils.dates import utcnow


class SourceConfig(Base, TimestampMixin):
    __tablename__ = "source_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    connector_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportExport(Base, TimestampMixin):
    __tablename__ = "report_exports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("patient_profiles.id", ondelete="SET NULL"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="completed")
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AppSettings(Base, TimestampMixin):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    default_profile_id: Mapped[int | None] = mapped_column(ForeignKey("patient_profiles.id", ondelete="SET NULL"), nullable=True)
    daily_run_time: Mapped[str] = mapped_column(String(10), default="08:30")
    default_report_style: Mapped[str] = mapped_column(String(40), default="clinical")
    default_report_length: Mapped[str] = mapped_column(String(40), default="daily_summary")
    enabled_source_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    timezone_label: Mapped[str] = mapped_column(String(80), default="local")
    report_output_dir: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    demo_profile_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiProviderConfig(Base, TimestampMixin):
    __tablename__ = "api_provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    api_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class OnboardingState(Base, TimestampMixin):
    __tablename__ = "onboarding_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_step: Mapped[str | None] = mapped_column(String(60), nullable=True)
    show_demo_profile_option: Mapped[bool] = mapped_column(Boolean, default=True)
    welcome_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    last_health_check: Mapped[dict] = mapped_column(JSON, default=dict)
