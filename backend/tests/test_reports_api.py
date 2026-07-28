from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.routes import reports as report_routes
from app.db.base import Base
from app.models.profile import PatientProfile
from app.models.settings import ReportExport
from app.services import audit_service


class ReportsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        # A single shared in-memory connection so the TestClient's worker
        # thread sees the same database as the test thread.
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        self._tmp = TemporaryDirectory()
        self._audit_patch = patch.object(
            audit_service,
            "get_app_paths",
            return_value=SimpleNamespace(logs_dir=Path(self._tmp.name)),
        )
        self._audit_patch.start()

        app = FastAPI()
        app.include_router(report_routes.router, prefix="/api/reports")

        def override_get_db():
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._audit_patch.stop()
        self._tmp.cleanup()
        self.engine.dispose()

    def _add_profile(self) -> int:
        with self.session_factory() as session:
            profile = PatientProfile(
                profile_name="Jane Patient Smith",
                cancer_type="NSCLC",
                would_consider=[],
                would_not_consider=[],
                is_active=True,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile.id

    def test_preview_returns_an_outline_without_writing_anything(self) -> None:
        self._add_profile()

        response = self.client.get("/api/reports/preview", params={"report_type": "appointment_prep"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["report_type"], "appointment_prep")
        self.assertEqual(payload["report_title"], "Appointment Prep Sheet")
        self.assertEqual([section["key"] for section in payload["sections"]], ["top_things_to_raise"])
        self.assertIn("counts", payload)
        # Preview must not create a report row or a file.
        self.assertEqual(self.client.get("/api/reports").json(), [])

    def test_preview_requires_a_profile(self) -> None:
        response = self.client.get("/api/reports/preview")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Create a patient profile first.")

    def test_generate_requires_a_profile(self) -> None:
        response = self.client.post("/api/reports/generate", json={"report_type": "daily_summary"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Create a patient profile first.")

    def test_unknown_report_type_is_rejected(self) -> None:
        self._add_profile()

        generated = self.client.post("/api/reports/generate", json={"report_type": "not_a_report"})
        previewed = self.client.get("/api/reports/preview", params={"report_type": "not_a_report"})

        self.assertEqual(generated.status_code, 422)
        self.assertEqual(previewed.status_code, 422)

    def test_download_reports_a_missing_row_and_a_missing_file_differently(self) -> None:
        profile_id = self._add_profile()
        with self.session_factory() as session:
            export = ReportExport(
                profile_id=profile_id,
                report_type="daily_summary",
                status="completed",
                file_path=str(Path(self._tmp.name) / "gone.pdf"),
                summary_json={},
            )
            session.add(export)
            session.commit()
            session.refresh(export)
            report_id = export.id

        missing_row = self.client.get("/api/reports/9999/download")
        missing_file = self.client.get(f"/api/reports/{report_id}/download")

        self.assertEqual(missing_row.status_code, 404)
        self.assertEqual(missing_row.json()["detail"], "Report not found")
        self.assertEqual(missing_file.status_code, 404)
        self.assertEqual(missing_file.json()["detail"], "Report file is missing from disk")

    def test_generate_then_download_serves_the_pdf(self) -> None:
        self._add_profile()
        reports_dir = Path(self._tmp.name) / "reports"
        reports_dir.mkdir()

        with patch(
            "app.services.report_service.get_app_paths",
            return_value=SimpleNamespace(reports_dir=reports_dir),
        ):
            generated = self.client.post("/api/reports/generate", json={"report_type": "appointment_prep"})

        self.assertEqual(generated.status_code, 200)
        body = generated.json()
        self.assertEqual(body["report_type"], "appointment_prep")
        self.assertEqual(body["summary_json"]["outline"]["report_title"], "Appointment Prep Sheet")

        downloaded = self.client.get(f"/api/reports/{body['id']}/download")

        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.headers["content-type"], "application/pdf")
        self.assertTrue(downloaded.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
