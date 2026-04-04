from __future__ import annotations

import logging
import os

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.paths import get_app_paths
from app.core.release import DEMO_FINDING_SOURCE_NAMES, DEMO_SOURCE_KEYS, PUBLIC_SOURCE_CATEGORIES, PUBLIC_SOURCE_KEYS
from app.db.migrations import ensure_schema_up_to_date
from app.db.session import SessionLocal
from app.models.finding import Finding
from app.models.run import MonitoringRun
from app.models.settings import ApiProviderConfig, AppSettings, OnboardingState, SourceConfig
from app.utils.dates import utcnow

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_CONFIGS = [
    {
        "category": "clinical_trials",
        "name": "ClinicalTrials.gov trials",
        "connector_key": "clinicaltrials_gov",
        "enabled": True,
        "settings_json": {
            "page_size": 10,
            "overall_statuses": [
                "RECRUITING",
                "NOT_YET_RECRUITING",
                "ENROLLING_BY_INVITATION",
                "ACTIVE_NOT_RECRUITING",
            ],
            "notes": "Live ClinicalTrials.gov connector with configurable result count and recruitment-status filters.",
        },
    },
    {
        "category": "literature",
        "name": "PubMed literature",
        "connector_key": "pubmed_literature",
        "enabled": True,
        "settings_json": {"retmax": 5},
    },
]


DISCLAIMER_TEXT = (
    "OncoWatch is an information monitoring and summarization tool. "
    "It does not determine treatment, trial eligibility, or medical appropriateness. "
    "All findings should be reviewed with a licensed oncology team."
)


def initialize_application() -> None:
    get_app_paths()
    ensure_schema_up_to_date()
    with SessionLocal() as session:
        _ensure_defaults(session)
        _recover_interrupted_runs(session)
    logger.info("OncoWatch local storage and database initialized.")


def _ensure_defaults(session: Session) -> None:
    app_settings = session.scalar(select(AppSettings))
    if app_settings is None:
        app_settings = AppSettings(
            daily_run_time="08:30",
            default_report_style="clinical",
            default_report_length="daily_summary",
            enabled_source_categories=sorted(PUBLIC_SOURCE_CATEGORIES),
        )
        session.add(app_settings)

    if session.scalar(select(OnboardingState.id)) is None:
        session.add(
            OnboardingState(
                is_completed=False,
                current_step="welcome",
                show_demo_profile_option=False,
                welcome_acknowledged=False,
                last_health_check={},
            )
        )

    if session.scalar(select(ApiProviderConfig.id).where(ApiProviderConfig.provider_key == "openrouter")) is None:
        session.add(
            ApiProviderConfig(
                provider_key="openrouter",
                display_name="OpenRouter",
                is_configured=False,
                api_base_url="https://openrouter.ai/api/v1",
                selected_model=None,
                metadata_json={"provider_family": "aggregator"},
            )
        )

    _migrate_trial_source_config(session)
    _disable_non_public_sources(session)
    _purge_demo_findings(session)

    existing = {
        row.connector_key
        for row in session.scalars(select(SourceConfig)).all()
    }
    for config in DEFAULT_SOURCE_CONFIGS:
        if config["connector_key"] not in existing:
            session.add(SourceConfig(**config))

    enabled_categories = sorted(
        {
            config.category
            for config in session.scalars(select(SourceConfig)).all()
            if config.enabled and config.connector_key in PUBLIC_SOURCE_KEYS
        }
    )
    app_settings.enabled_source_categories = enabled_categories or sorted(PUBLIC_SOURCE_CATEGORIES)
    app_settings.demo_profile_enabled = False
    session.commit()


def _migrate_trial_source_config(session: Session) -> None:
    legacy = session.scalar(select(SourceConfig).where(SourceConfig.connector_key == "demo_trials"))
    current = session.scalar(select(SourceConfig).where(SourceConfig.connector_key == "clinicaltrials_gov"))
    default_settings = DEFAULT_SOURCE_CONFIGS[0]["settings_json"]

    if legacy is not None and current is None:
        legacy.category = "clinical_trials"
        legacy.name = "ClinicalTrials.gov trials"
        legacy.connector_key = "clinicaltrials_gov"
        legacy.settings_json = {**default_settings, **(legacy.settings_json or {})}
        return

    if current is not None:
        current.category = "clinical_trials"
        current.name = "ClinicalTrials.gov trials"
        current.settings_json = {**default_settings, **(current.settings_json or {})}

    if legacy is not None and current is not None:
        legacy.enabled = False
        legacy.name = "Legacy demo clinical trials feed"


def _disable_non_public_sources(session: Session) -> None:
    if _allow_demo_content():
        return
    for source in session.scalars(select(SourceConfig)).all():
        if source.connector_key not in DEMO_SOURCE_KEYS:
            continue
        source.enabled = False
        if source.connector_key == "demo_drug_updates":
            source.name = "Contributor demo drug feed"
        elif source.connector_key == "demo_biomarker":
            source.name = "Contributor demo biomarker feed"
        elif source.connector_key == "demo_trials":
            source.name = "Contributor demo clinical trials feed"


def _purge_demo_findings(session: Session) -> None:
    if _allow_demo_content():
        return
    demo_findings = session.scalars(
        select(Finding).where(
            or_(
                Finding.source_name.in_(tuple(DEMO_FINDING_SOURCE_NAMES)),
                Finding.external_identifier.like("DEMO-%"),
            )
        )
    ).all()
    for finding in demo_findings:
        session.delete(finding)


def _recover_interrupted_runs(session: Session) -> None:
    running_runs = session.scalars(
        select(MonitoringRun).where(
            MonitoringRun.status == "running",
            MonitoringRun.completed_at.is_(None),
        )
    ).all()
    if not running_runs:
        return

    for run in running_runs:
        run.status = "failed"
        run.completed_at = utcnow()
        if not run.error_text:
            run.error_text = "The previous monitoring run stopped when OncoWatch closed or restarted."
    session.commit()


def _allow_demo_content() -> bool:
    return os.getenv("ONCOWATCH_ALLOW_DEMO_CONTENT") == "1"
