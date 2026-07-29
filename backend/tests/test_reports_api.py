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
from app.models.settings import AppSettings, ReportExport
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

    def _add_profile(self, *, name: str = "Jane Patient Smith", active: bool = True) -> int:
        with self.session_factory() as session:
            profile = PatientProfile(
                profile_name=name,
                cancer_type="NSCLC",
                would_consider=[],
                would_not_consider=[],
                is_active=active,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile.id

    def _add_report(self, profile_id: int | None, *, file_path: str, report_type: str = "daily_summary") -> int:
        with self.session_factory() as session:
            export = ReportExport(
                profile_id=profile_id,
                report_type=report_type,
                status="completed",
                file_path=file_path,
                summary_json={},
            )
            session.add(export)
            session.commit()
            session.refresh(export)
            return export.id

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
        self.assertEqual(self.client.get("/api/reports").json(), {"items": [], "other_profiles_count": 0})

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
        report_id = self._add_report(profile_id, file_path=str(Path(self._tmp.name) / "gone.pdf"))

        missing_row = self.client.get("/api/reports/9999/download")
        missing_file = self.client.get(f"/api/reports/{report_id}/download")

        self.assertEqual(missing_row.status_code, 404)
        self.assertEqual(missing_row.json()["detail"], "Report not found")
        self.assertEqual(missing_file.status_code, 404)
        self.assertEqual(missing_file.json()["detail"], "Report file is missing from disk")

    def test_list_scopes_to_the_active_profile_and_counts_the_rest(self) -> None:
        active_id = self._add_profile()
        other_id = self._add_profile(name="Second Person", active=False)
        # Pin the active profile explicitly — the resolver prefers
        # AppSettings.default_profile_id over recency.
        with self.session_factory() as session:
            session.add(
                AppSettings(
                    daily_run_time="08:30",
                    default_report_style="clinical",
                    default_report_length="daily_summary",
                    enabled_source_categories=["clinical_trials"],
                    default_profile_id=active_id,
                )
            )
            session.commit()
        mine = self._add_report(active_id, file_path=str(Path(self._tmp.name) / "mine.pdf"))
        self._add_report(other_id, file_path=str(Path(self._tmp.name) / "theirs.pdf"))
        # A report whose profile was deleted must stay visible everywhere.
        orphan = self._add_report(None, file_path=str(Path(self._tmp.name) / "orphan.pdf"))

        payload = self.client.get("/api/reports").json()

        self.assertEqual({item["id"] for item in payload["items"]}, {mine, orphan})
        self.assertEqual(payload["other_profiles_count"], 1)

    def test_list_marks_reports_whose_file_is_gone(self) -> None:
        profile_id = self._add_profile()
        present_path = Path(self._tmp.name) / "present.pdf"
        present_path.write_bytes(b"%PDF-fake")
        present = self._add_report(profile_id, file_path=str(present_path))
        missing = self._add_report(profile_id, file_path=str(Path(self._tmp.name) / "vanished.pdf"))

        by_id = {item["id"]: item for item in self.client.get("/api/reports").json()["items"]}

        self.assertTrue(by_id[present]["file_exists"])
        self.assertFalse(by_id[missing]["file_exists"])

    def test_delete_removes_the_row_and_the_file(self) -> None:
        profile_id = self._add_profile()
        pdf_path = Path(self._tmp.name) / "delete-me.pdf"
        pdf_path.write_bytes(b"%PDF-fake")
        report_id = self._add_report(profile_id, file_path=str(pdf_path))

        response = self.client.delete(f"/api/reports/{report_id}")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(pdf_path.exists())
        self.assertEqual(self.client.get("/api/reports").json()["items"], [])

    def test_delete_succeeds_when_the_file_is_already_gone(self) -> None:
        profile_id = self._add_profile()
        report_id = self._add_report(profile_id, file_path=str(Path(self._tmp.name) / "already-gone.pdf"))

        response = self.client.delete(f"/api/reports/{report_id}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/reports").json()["items"], [])

    def test_delete_unknown_report_returns_404(self) -> None:
        self._add_profile()
        response = self.client.delete("/api/reports/9999")
        self.assertEqual(response.status_code, 404)

    def test_generate_accepts_appointment_details_without_persisting_them(self) -> None:
        self._add_profile()
        reports_dir = Path(self._tmp.name) / "reports"
        reports_dir.mkdir()

        with patch(
            "app.services.report_service.get_app_paths",
            return_value=SimpleNamespace(reports_dir=reports_dir),
        ):
            response = self.client.post(
                "/api/reports/generate",
                json={
                    "report_type": "appointment_prep",
                    "appointment_date": "2026-08-05",
                    "appointment_clinician": "Dr. Rivera",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["file_exists"])
        persisted = str(body["summary_json"])
        self.assertNotIn("Rivera", persisted)
        self.assertNotIn("2026-08-05", persisted)

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
