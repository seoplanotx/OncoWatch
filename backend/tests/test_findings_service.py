from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.connectors.base import ConnectorRecord
from app.models import Biomarker, PatientProfile
from app.services.findings_service import upsert_finding
from app.services.matching_service import evaluate


def build_profile_record() -> PatientProfile:
    profile = PatientProfile(
        profile_name="Sample EGFR NSCLC",
        cancer_type="Non-small cell lung cancer",
        subtype="Adenocarcinoma",
        stage_or_context="Metastatic",
        location_label="Dallas, Texas",
        would_consider=["clinical trials"],
        would_not_consider=[],
        is_active=True,
    )
    profile.biomarkers = [Biomarker(name="EGFR", variant="Exon 19 deletion")]
    return profile


class FindingsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_upsert_marks_changed_when_normalized_facts_change(self) -> None:
        with self.session_factory() as session:
            profile = build_profile_record()
            session.add(profile)
            session.commit()
            session.refresh(profile)

            base_record = ConnectorRecord(
                category="clinical_trials",
                title="EGFR-directed study",
                source_name="ClinicalTrials.gov",
                source_url="https://clinicaltrials.gov/study/NCT12345678",
                external_identifier="NCT12345678",
                summary="Trial summary unchanged.",
                tags=["EGFR", "NSCLC"],
                published_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
                location_summary="Dallas, Texas",
                raw_payload={
                    "recruitment_status": "RECRUITING",
                    "conditions": ["Non-small Cell Lung Cancer", "EGFR exon 19 deletion"],
                    "locations": ["Dallas, Texas"],
                    "phases": ["Phase 2"],
                },
                evidence_label="Study summary",
                evidence_snippet="Recruiting study in Dallas.",
            )
            initial_match = evaluate(profile, base_record)
            finding, state = upsert_finding(
                session,
                profile_id=profile.id,
                monitoring_run_id=None,
                record=base_record,
                match=initial_match,
            )
            self.assertEqual(state, "new")
            self.assertEqual(finding.external_identifier, "NCT12345678")

            changed_record = ConnectorRecord(
                category="clinical_trials",
                title="EGFR-directed study",
                source_name="ClinicalTrials.gov",
                source_url="https://clinicaltrials.gov/study/NCT12345678",
                external_identifier="NCT12345678",
                summary="Trial summary unchanged.",
                tags=["EGFR", "NSCLC"],
                published_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
                location_summary="Dallas, Texas",
                raw_payload={
                    "recruitment_status": "COMPLETED",
                    "conditions": ["Non-small Cell Lung Cancer", "EGFR exon 19 deletion"],
                    "locations": ["Dallas, Texas"],
                    "phases": ["Phase 2"],
                },
                evidence_label="Study summary",
                evidence_snippet="Completed study in Dallas.",
            )
            changed_match = evaluate(profile, changed_record, is_new=False)
            finding, state = upsert_finding(
                session,
                profile_id=profile.id,
                monitoring_run_id=None,
                record=changed_record,
                match=changed_match,
            )

            self.assertEqual(state, "changed")
            self.assertEqual(finding.status, "changed")
            self.assertEqual(finding.match_debug["normalized_facts"]["record"]["recruitment_bucket"], "closed")
