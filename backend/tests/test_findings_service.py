from __future__ import annotations

from datetime import datetime, timezone
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.connectors.base import ConnectorRecord
from app.models import Biomarker, Finding, FindingEvidence, MonitoringRun, PatientProfile
from app.services.findings_service import build_briefing_snapshot, list_findings, upsert_finding
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


def build_finding(
    *,
    profile_id: int,
    monitoring_run_id: int | None,
    external_identifier: str,
    title: str,
    finding_type: str,
    status: str,
    score: float,
    relevance_label: str,
    published_at: datetime,
    updated_at: datetime,
    recruitment_bucket: str | None = None,
    freshness_bucket: str | None = None,
    gaps: list[str] | None = None,
) -> Finding:
    finding = Finding(
        profile_id=profile_id,
        monitoring_run_id=monitoring_run_id,
        type=finding_type,
        title=title,
        source_name="ClinicalTrials.gov" if finding_type == "clinical_trials" else "PubMed",
        source_url=f"https://example.org/{external_identifier}",
        external_identifier=external_identifier,
        retrieved_at=updated_at,
        published_at=published_at,
        structured_tags=[],
        raw_summary=f"Raw summary for {title}",
        normalized_summary=f"Normalized summary for {title}",
        why_it_surfaced=f"Why {title} surfaced",
        why_it_may_not_fit=None,
        confidence="high" if relevance_label == "High relevance" else "medium",
        score=score,
        relevance_label=relevance_label,
        status=status,
        location_summary="Dallas, Texas",
        matching_gaps=gaps or [],
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
        created_at=updated_at,
        updated_at=updated_at,
    )
    finding.evidence_items = [
        FindingEvidence(
            label="Evidence excerpt",
            snippet=f"Evidence for {title}",
            source_url=f"https://example.org/{external_identifier}",
            source_identifier=external_identifier,
            published_at=published_at,
            created_at=updated_at,
            updated_at=updated_at,
        )
    ]
    return finding


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

    def test_upsert_marks_existing_item_unchanged_when_hash_matches(self) -> None:
        with self.session_factory() as session:
            profile = build_profile_record()
            session.add(profile)
            session.commit()
            session.refresh(profile)

            record = ConnectorRecord(
                category="literature",
                title="EGFR ctDNA update",
                source_name="PubMed",
                source_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
                external_identifier="12345678",
                summary="Fresh literature update.",
                tags=["EGFR"],
                published_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
                raw_payload={"journal": "JCO", "abstract_text": "Fresh literature update."},
                evidence_label="Abstract excerpt",
                evidence_snippet="Fresh literature update.",
            )

            match = evaluate(profile, record)
            finding, state = upsert_finding(
                session,
                profile_id=profile.id,
                monitoring_run_id=None,
                record=record,
                match=match,
            )
            self.assertEqual(state, "new")
            self.assertEqual(finding.status, "new")

            repeat_match = evaluate(profile, record, is_new=False)
            finding, state = upsert_finding(
                session,
                profile_id=profile.id,
                monitoring_run_id=None,
                record=record,
                match=repeat_match,
            )

            self.assertEqual(state, "unchanged")
            self.assertEqual(finding.status, "unchanged")

    def test_briefing_snapshot_prioritizes_new_changed_trials_updates_and_blockers(self) -> None:
        with self.session_factory() as session:
            profile = build_profile_record()
            session.add(profile)
            session.commit()
            session.refresh(profile)

            run = MonitoringRun(
                profile_id=profile.id,
                status="completed",
                triggered_by="manual",
                started_at=datetime(2026, 3, 27, 4, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 3, 27, 4, 5, tzinfo=timezone.utc),
                new_findings_count=2,
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
                    external_identifier="NCT-NEW-OPEN",
                    title="New recruiting EGFR trial",
                    finding_type="clinical_trials",
                    status="new",
                    score=91.0,
                    relevance_label="High relevance",
                    published_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 3, 27, 4, 2, tzinfo=timezone.utc),
                    recruitment_bucket="open",
                    freshness_bucket="very_recent",
                    gaps=["Performance status was not available."],
                ),
                build_finding(
                    profile_id=profile.id,
                    monitoring_run_id=run.id,
                    external_identifier="LIT-NEW",
                    title="New EGFR resistance literature",
                    finding_type="literature",
                    status="new",
                    score=67.0,
                    relevance_label="Worth reviewing",
                    published_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 3, 27, 4, 1, tzinfo=timezone.utc),
                    freshness_bucket="very_recent",
                    gaps=["Performance status was not available."],
                ),
                build_finding(
                    profile_id=profile.id,
                    monitoring_run_id=run.id,
                    external_identifier="NCT-CHANGED",
                    title="Changed closed EGFR trial",
                    finding_type="clinical_trials",
                    status="changed",
                    score=79.0,
                    relevance_label="Worth reviewing",
                    published_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 3, 27, 4, 3, tzinfo=timezone.utc),
                    recruitment_bucket="closed",
                    freshness_bucket="recent",
                    gaps=["Eligibility criteria excerpt was not available."],
                ),
                build_finding(
                    profile_id=profile.id,
                    monitoring_run_id=run.id,
                    external_identifier="NCT-UNCHANGED",
                    title="Open trial worth reviewing",
                    finding_type="clinical_trials",
                    status="unchanged",
                    score=84.0,
                    relevance_label="High relevance",
                    published_at=datetime(2026, 3, 18, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 3, 27, 4, 4, tzinfo=timezone.utc),
                    recruitment_bucket="open",
                    freshness_bucket="recent",
                    gaps=["Travel feasibility is not clear from the site list."],
                ),
                build_finding(
                    profile_id=profile.id,
                    monitoring_run_id=run.id,
                    external_identifier="DRUG-UNCHANGED",
                    title="Recent drug update",
                    finding_type="drug_updates",
                    status="unchanged",
                    score=61.0,
                    relevance_label="Worth reviewing",
                    published_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 3, 27, 4, 4, tzinfo=timezone.utc),
                    freshness_bucket="very_recent",
                    gaps=["Abstract text was not available from PubMed for this citation."],
                ),
            ]
            session.add_all(findings)
            session.commit()

            run.summary_json = {
                "new_finding_ids": [findings[0].id, findings[1].id],
                "changed_finding_ids": [findings[2].id],
            }
            session.commit()
            session.refresh(run)

            ordered = list_findings(session, profile_id=profile.id)
            snapshot = build_briefing_snapshot(ordered, latest_run=run)

            self.assertEqual([item.title for item in ordered[:3]], [
                "New recruiting EGFR trial",
                "New EGFR resistance literature",
                "Changed closed EGFR trial",
            ])
            self.assertEqual(snapshot["new_count"], 2)
            self.assertEqual(snapshot["changed_count"], 1)
            self.assertEqual([section["key"] for section in snapshot["sections"]], [
                "new_findings",
                "changed_findings",
                "top_trial_matches",
                "top_literature_updates",
            ])
            self.assertEqual(
                [item.title for item in snapshot["sections"][0]["items"]],
                ["New recruiting EGFR trial", "New EGFR resistance literature"],
            )
            self.assertEqual(
                [item.title for item in snapshot["sections"][1]["items"]],
                ["Changed closed EGFR trial"],
            )
            self.assertEqual(
                [item.title for item in snapshot["sections"][2]["items"]],
                ["Open trial worth reviewing"],
            )
            self.assertEqual(
                [item.title for item in snapshot["sections"][3]["items"]],
                ["Recent drug update"],
            )
            self.assertEqual(snapshot["blockers"][0]["label"], "Performance status was not available.")
            self.assertEqual(snapshot["blockers"][0]["finding_count"], 2)
