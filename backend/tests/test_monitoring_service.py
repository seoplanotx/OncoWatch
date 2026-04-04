from __future__ import annotations

from datetime import datetime, timezone
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import MonitoringRun, PatientProfile
from app.services.monitoring_service import RunConflictError, run_monitoring


class MonitoringServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_rejects_overlapping_run_when_existing_run_is_marked_running(self) -> None:
        with self.session_factory() as session:
            profile = PatientProfile(
                profile_name="Sample",
                cancer_type="NSCLC",
                would_consider=[],
                would_not_consider=[],
                is_active=True,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)

            session.add(
                MonitoringRun(
                    profile_id=profile.id,
                    status="running",
                    triggered_by="manual",
                    started_at=datetime(2026, 4, 3, 10, 0, tzinfo=timezone.utc),
                    summary_json={"connectors": []},
                    sources_checked=[],
                )
            )
            session.commit()

            with self.assertRaises(RunConflictError):
                run_monitoring(session, profile_id=profile.id, triggered_by="manual")
