from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.paths import get_app_paths
from app.db.session import SessionLocal, init_db
from app.models.settings import ApiProviderConfig, AppSettings, OnboardingState, SourceConfig

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
    {
        "category": "drug_updates",
        "name": "Drug and label updates starter feed",
        "connector_key": "demo_drug_updates",
        "enabled": True,
        "settings_json": {},
    },
    {
        "category": "biomarker",
        "name": "Biomarker updates starter feed",
        "connector_key": "demo_biomarker",
        "enabled": True,
        "settings_json": {},
    },
]


DISCLAIMER_TEXT = (
    "OncoWatch is an information monitoring and summarization tool. "
    "It does not determine treatment, trial eligibility, or medical appropriateness. "
    "All findings should be reviewed with a licensed oncology team."
)


def initialize_application() -> None:
    get_app_paths()
    init_db()
    with SessionLocal() as session:
        _ensure_defaults(session)
    logger.info("OncoWatch local storage and database initialized.")


def _ensure_defaults(session: Session) -> None:
    if session.scalar(select(AppSettings.id)) is None:
        session.add(
            AppSettings(
                daily_run_time="08:30",
                default_report_style="clinical",
                default_report_length="daily_summary",
                enabled_source_categories=["clinical_trials", "literature", "drug_updates", "biomarker"],
            )
        )

    if session.scalar(select(OnboardingState.id)) is None:
        session.add(
            OnboardingState(
                is_completed=False,
                current_step="welcome",
                show_demo_profile_option=True,
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

    existing = {
        row.connector_key
        for row in session.scalars(select(SourceConfig)).all()
    }
    for config in DEFAULT_SOURCE_CONFIGS:
        if config["connector_key"] not in existing:
            session.add(SourceConfig(**config))

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
