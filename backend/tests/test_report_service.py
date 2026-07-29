from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import AppSettings, Biomarker, Finding, FindingEvidence, MonitoringRun, PatientProfile
from app.services.llm_service import validate_clinician_questions
from app.services.report_service import (
    APPOINTMENT_PREP_TOP_ITEMS,
    _report_title,
    _trimmed_profile_rows,
    build_report_bytes,
    build_report_outline,
    _deterministic_questions,
    write_report,
)


def build_profile() -> PatientProfile:
    profile = PatientProfile(
        profile_name="Sample EGFR NSCLC",
        cancer_type="Non-small cell lung cancer",
        subtype="Adenocarcinoma",
        stage_or_context="Metastatic",
        current_therapy_status="Discussing next line therapy",
        location_label="Dallas, Texas",
        would_consider=["clinical trials"],
        would_not_consider=[],
        is_active=True,
    )
    profile.biomarkers = [Biomarker(name="EGFR", variant="Exon 19 deletion")]
    return profile


def build_finding(
    *,
    profile_id: int,
    monitoring_run_id: int,
    title: str,
    external_identifier: str,
    finding_type: str,
    status: str,
    score: float,
    relevance_label: str,
    recruitment_bucket: str | None = None,
    freshness_bucket: str | None = None,
) -> Finding:
    timestamp = datetime(2026, 3, 27, 4, 0, tzinfo=timezone.utc)
    finding = Finding(
        profile_id=profile_id,
        monitoring_run_id=monitoring_run_id,
        type=finding_type,
        title=title,
        source_name="ClinicalTrials.gov" if finding_type == "clinical_trials" else "PubMed",
        source_url=f"https://example.org/{external_identifier}",
        external_identifier=external_identifier,
        retrieved_at=timestamp,
        published_at=timestamp,
        structured_tags=[],
        raw_summary=f"Raw summary for {title}",
        normalized_summary=f"Normalized summary for {title}",
        why_it_surfaced=f"Why {title} surfaced",
        why_it_may_not_fit=None,
        confidence="high",
        score=score,
        relevance_label=relevance_label,
        status=status,
        location_summary="Dallas, Texas",
        matching_gaps=["Performance status was not available."],
        match_debug={
            "normalized_facts": {
                "record": {
                    "recruitment_bucket": recruitment_bucket,
                    "evidence_freshness_bucket": freshness_bucket,
                }
            }
        },
        content_hash=f"hash-{external_identifier}",
        llm_metadata={},
        created_at=timestamp,
        updated_at=timestamp,
    )
    finding.evidence_items = [
        FindingEvidence(
            label="Evidence excerpt",
            snippet=f"Evidence for {title}",
            source_url=f"https://example.org/{external_identifier}",
            source_identifier=external_identifier,
            published_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
    ]
    return finding


class ReportServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_write_report_stores_briefing_summary_json(self) -> None:
        with self.session_factory() as session:
            session.add(
                AppSettings(
                    daily_run_time="08:30",
                    default_report_style="clinical",
                    default_report_length="daily_summary",
                    enabled_source_categories=["clinical_trials", "literature"],
                )
            )
            profile = build_profile()
            session.add(profile)
            session.commit()
            session.refresh(profile)

            run = MonitoringRun(
                profile_id=profile.id,
                status="completed",
                triggered_by="manual",
                started_at=datetime(2026, 3, 27, 4, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 3, 27, 4, 5, tzinfo=timezone.utc),
                new_findings_count=1,
                changed_findings_count=1,
                summary_json={},
                sources_checked=[],
            )
            session.add(run)
            session.commit()
            session.refresh(run)

            findings = [
                build_finding(
                    profile_id=profile.id,
                    monitoring_run_id=run.id,
                    title="New recruiting EGFR trial",
                    external_identifier="NCT-NEW-OPEN",
                    finding_type="clinical_trials",
                    status="new",
                    score=91.0,
                    relevance_label="High relevance",
                    recruitment_bucket="open",
                    freshness_bucket="very_recent",
                ),
                build_finding(
                    profile_id=profile.id,
                    monitoring_run_id=run.id,
                    title="Changed EGFR literature update",
                    external_identifier="LIT-CHANGED",
                    finding_type="literature",
                    status="changed",
                    score=73.0,
                    relevance_label="Worth reviewing",
                    freshness_bucket="recent",
                ),
            ]
            session.add_all(findings)
            session.commit()

            run.summary_json = {
                "new_finding_ids": [findings[0].id],
                "changed_finding_ids": [findings[1].id],
            }
            session.commit()

            fake_paths = type("Paths", (), {"reports_dir": Path("/virtual/reports")})()
            report_timestamp = datetime(2026, 3, 27, 4, 58, 24, tzinfo=timezone.utc)
            with patch("app.services.report_service.get_app_paths", return_value=fake_paths):
                with patch("app.services.report_service.utcnow", return_value=report_timestamp):
                    with patch("pathlib.Path.write_bytes", return_value=1024) as write_bytes:
                        export = write_report(session, profile=profile, findings=findings, report_type="daily_summary")

            write_bytes.assert_called_once()
            self.assertEqual(export.file_path, "/virtual/reports/20260327-045824-daily_summary-sample-egfr-nsclc.pdf")

            self.assertEqual(export.summary_json["new_count"], 1)
            self.assertEqual(export.summary_json["changed_count"], 1)
            self.assertEqual(
                [section["key"] for section in export.summary_json["sections"]],
                ["new_findings", "changed_findings", "top_trial_matches", "top_literature_updates"],
            )
            self.assertEqual(export.summary_json["sections"][0]["items"][0]["title"], "New recruiting EGFR trial")
            # The patient name must not be persisted in the DB summary JSON.
            self.assertNotIn("profile_name", export.summary_json)
            self.assertEqual(export.summary_json["report_title"], "Daily Summary Report")

            # The outline drives the in-app view of this report.
            outline = export.summary_json["outline"]
            self.assertEqual(outline["report_type"], "daily_summary")
            self.assertEqual(outline["report_title"], "Daily Summary Report")
            self.assertEqual(
                [section["key"] for section in outline["sections"]],
                ["new_findings", "changed_findings", "top_trial_matches", "top_literature_updates"],
            )
            self.assertEqual(outline["sections"][0]["items"][0]["title"], "New recruiting EGFR trial")
            self.assertEqual(outline["sections"][0]["items"][0]["identifier"], "NCT-NEW-OPEN")
            self.assertTrue(outline["questions"])
            self.assertEqual(outline["counts"]["findings"], 2)
            self.assertEqual(outline["counts"]["new"], 1)
            self.assertEqual(outline["counts"]["changed"], 1)
            # The no-identifying-data rule covers the outline too.
            self.assertNotIn("profile_name", json.dumps(outline))
            self.assertNotIn(profile.profile_name, json.dumps(outline))

    def test_appointment_prep_outline_caps_top_things_to_raise(self) -> None:
        profile = build_profile()
        findings = [
            build_finding(
                profile_id=1,
                monitoring_run_id=1,
                title=f"Trial {index}",
                external_identifier=f"NCT-{index}",
                finding_type="clinical_trials",
                status="new",
                score=90.0 - index,
                relevance_label="High relevance",
                recruitment_bucket="open",
            )
            for index in range(APPOINTMENT_PREP_TOP_ITEMS + 4)
        ]
        briefing = {
            "new_count": len(findings),
            "changed_count": 0,
            "blockers": [{"label": "Performance status", "finding_count": 3, "examples": ["Trial 0"]}],
        }

        outline = build_report_outline(profile, findings, "appointment_prep", briefing=briefing)

        self.assertEqual([section["key"] for section in outline["sections"]], ["top_things_to_raise"])
        self.assertEqual(len(outline["sections"][0]["items"]), APPOINTMENT_PREP_TOP_ITEMS)
        # The prep sheet has no evidence appendix — that is what full_review is for.
        self.assertEqual(outline["counts"]["appendix"], 0)
        self.assertLessEqual(len(outline["questions"]), 5)
        self.assertEqual(outline["gaps"][0]["label"], "Performance status")

    def test_full_review_outline_counts_the_evidence_appendix(self) -> None:
        profile = build_profile()
        findings = [
            build_finding(
                profile_id=1,
                monitoring_run_id=1,
                title=f"Trial {index}",
                external_identifier=f"NCT-{index}",
                finding_type="clinical_trials",
                status="new",
                score=90.0 - index,
                relevance_label="High relevance",
                recruitment_bucket="open",
            )
            for index in range(3)
        ]
        for index, finding in enumerate(findings):
            finding.id = index + 1
        briefing = {
            "new_count": 3,
            "changed_count": 0,
            "sections": [
                {
                    "key": "new_findings",
                    "title": "New findings",
                    "description": "Items first seen in the latest monitoring cycle.",
                    "empty_message": "No new findings were detected in the latest run.",
                    "count": 3,
                    "items": findings[:2],
                }
            ],
            "blockers": [],
        }

        outline = build_report_outline(profile, findings, "full_review", briefing=briefing)

        self.assertEqual(outline["report_title"], "Full Oncology Review Report")
        self.assertEqual(len(outline["sections"][0]["items"]), 2)
        self.assertEqual(outline["sections"][0]["count"], 3)
        # Section items plus the ranked backfill that only full_review gets.
        self.assertEqual(outline["counts"]["appendix"], 3)

    def test_report_deterministic_questions_pass_clinician_review_safety_policy(self) -> None:
        profile = build_profile()
        finding = build_finding(
            profile_id=1,
            monitoring_run_id=1,
            title="New recruiting EGFR trial",
            external_identifier="NCT-NEW-OPEN",
            finding_type="clinical_trials",
            status="new",
            score=91.0,
            relevance_label="High relevance",
            recruitment_bucket="open",
            freshness_bucket="very_recent",
        )

        questions = _deterministic_questions(profile, [finding])

        self.assertTrue(questions)
        self.assertEqual(validate_clinician_questions(questions), questions)

    def test_report_title_maps_appointment_prep(self) -> None:
        self.assertEqual(_report_title("appointment_prep"), "Appointment Prep Sheet")
        self.assertEqual(_report_title("daily_summary"), "Daily Summary Report")
        self.assertEqual(_report_title("unknown_type"), "Full Oncology Review Report")

    def test_trimmed_profile_rows_drop_display_name_and_empties(self) -> None:
        profile = build_profile()
        rows = _trimmed_profile_rows(profile)
        labels = [row[0] for row in rows]
        self.assertNotIn("Display name", labels)
        for row in rows:
            self.assertNotIn(row[1], (None, "", "—"))

    def test_appointment_prep_report_renders_pdf_bytes(self) -> None:
        profile = build_profile()
        finding = build_finding(
            profile_id=1,
            monitoring_run_id=1,
            title="New recruiting EGFR trial",
            external_identifier="NCT-NEW-OPEN",
            finding_type="clinical_trials",
            status="new",
            score=91.0,
            relevance_label="High relevance",
            recruitment_bucket="open",
            freshness_bucket="very_recent",
        )

        briefing = {
            "new_count": 1,
            "changed_count": 0,
            "blockers": [
                {"label": "Performance status", "finding_count": 1, "examples": ["New recruiting EGFR trial"]}
            ],
        }
        pdf_bytes = build_report_bytes(profile, [finding], "appointment_prep", briefing=briefing)

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)


if __name__ == "__main__":
    unittest.main()
