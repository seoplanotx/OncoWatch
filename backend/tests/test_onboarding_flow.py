from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.routes.bootstrap import get_bootstrap
from app.api.routes.onboarding import complete_onboarding
from app.db.base import Base
from app.models import AppSettings, OnboardingState
from app.schemas.health import HealthCheckItem, HealthCheckResponse
from app.schemas.onboarding import OnboardingCompleteRequest
from app.services.dashboard_service import get_dashboard
from app.services.profile_service import create_demo_profile


def build_health_response() -> HealthCheckResponse:
    return HealthCheckResponse(
        checked_at=datetime(2026, 3, 27, 4, 30, tzinfo=timezone.utc),
        overall_ok=True,
        items=[HealthCheckItem(key="storage", label="Local storage", ok=True, message="ready")],
    )


class OnboardingFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_complete_onboarding_serializes_health_snapshot_for_json_storage(self) -> None:
        health = build_health_response()

        with self.session_factory() as session:
            with patch("app.api.routes.onboarding.run_health_check", return_value=health):
                state = complete_onboarding(OnboardingCompleteRequest(), session)

            stored = session.scalar(select(OnboardingState))
            self.assertIsNotNone(stored)
            self.assertTrue(state.is_completed)
            self.assertIsInstance(stored.last_health_check["checked_at"], str)
            parsed = datetime.fromisoformat(stored.last_health_check["checked_at"].replace("Z", "+00:00"))
            self.assertEqual(parsed, health.checked_at)
            self.assertTrue(stored.last_health_check["overall_ok"])

    def test_completed_onboarding_allows_bootstrap_and_dashboard_to_load_cleanly(self) -> None:
        health = build_health_response()

        with self.session_factory() as session:
            settings = AppSettings(
                daily_run_time="08:30",
                default_report_style="clinical",
                default_report_length="daily_summary",
                enabled_source_categories=["clinical_trials", "literature", "drug_updates", "biomarker"],
            )
            session.add(settings)
            session.commit()

            profile = create_demo_profile(session)
            settings.default_profile_id = profile.id
            session.commit()

            with patch("app.api.routes.onboarding.run_health_check", return_value=health):
                state = complete_onboarding(OnboardingCompleteRequest(), session)

            fake_paths = SimpleNamespace(
                data_dir=Path("/tmp/oncowatch-data"),
                reports_dir=Path("/tmp/oncowatch-data/reports"),
            )
            with patch("app.api.routes.bootstrap.get_app_paths", return_value=fake_paths):
                bootstrap = get_bootstrap(session)

            dashboard = get_dashboard(session)

            self.assertTrue(state.is_completed)
            self.assertTrue(bootstrap.onboarding_completed)
            self.assertEqual(bootstrap.active_profile_id, profile.id)
            self.assertEqual(dashboard.counts["total_findings"], 0)
            self.assertEqual(dashboard.recent_findings, [])
            self.assertEqual(dashboard.briefing.new_count, 0)
            self.assertEqual(dashboard.briefing.changed_count, 0)
            self.assertEqual([section.key for section in dashboard.briefing.sections], [
                "new_findings",
                "changed_findings",
                "top_trial_matches",
                "top_literature_updates",
            ])
