from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import AppSettings, Biomarker, Finding, FindingEvidence, MonitoringRun, PatientProfile
from app.services.report_service import write_report


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
