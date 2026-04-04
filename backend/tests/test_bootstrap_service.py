from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import AppSettings, SourceConfig
from app.services.bootstrap_service import _ensure_defaults, _migrate_trial_source_config


class BootstrapServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_migrates_legacy_demo_trials_config_in_place(self) -> None:
        with self.session_factory() as session:
            legacy = SourceConfig(
                category="clinical_trials",
                name="Demo trial feed",
                connector_key="demo_trials",
                enabled=True,
                settings_json={"page_size": 6},
            )
            session.add(legacy)
            session.commit()

            _migrate_trial_source_config(session)

            self.assertEqual(legacy.connector_key, "clinicaltrials_gov")
            self.assertEqual(legacy.name, "ClinicalTrials.gov trials")
            self.assertEqual(legacy.category, "clinical_trials")
            self.assertEqual(legacy.settings_json["page_size"], 6)
            self.assertIn("overall_statuses", legacy.settings_json)

    def test_disables_legacy_demo_trials_when_current_source_exists(self) -> None:
        with self.session_factory() as session:
            legacy = SourceConfig(
                category="clinical_trials",
                name="Demo trial feed",
                connector_key="demo_trials",
                enabled=True,
                settings_json={"page_size": 4},
            )
            current = SourceConfig(
                category="clinical_trials",
                name="ClinicalTrials.gov trials",
                connector_key="clinicaltrials_gov",
                enabled=True,
                settings_json={"page_size": 25},
            )
            session.add_all([legacy, current])
            session.commit()

            _migrate_trial_source_config(session)

            self.assertEqual(current.connector_key, "clinicaltrials_gov")
            self.assertEqual(current.settings_json["page_size"], 25)
            self.assertIn("overall_statuses", current.settings_json)
            self.assertFalse(legacy.enabled)
            self.assertEqual(legacy.connector_key, "demo_trials")
            self.assertEqual(legacy.name, "Legacy demo clinical trials feed")

    def test_public_release_defaults_only_create_real_sources(self) -> None:
        with self.session_factory() as session:
            _ensure_defaults(session)

            settings = session.query(AppSettings).one()
            sources = session.query(SourceConfig).order_by(SourceConfig.connector_key).all()

            self.assertEqual(settings.enabled_source_categories, ["clinical_trials", "literature"])
            self.assertEqual([source.connector_key for source in sources], ["clinicaltrials_gov", "pubmed_literature"])
