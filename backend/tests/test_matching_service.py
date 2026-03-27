from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.connectors.base import ConnectorRecord
from app.services.matching_service import evaluate


def build_profile() -> SimpleNamespace:
    return SimpleNamespace(
        cancer_type="Non-small cell lung cancer",
        subtype="Adenocarcinoma",
        stage_or_context="Metastatic",
        location_label="Dallas, Texas",
        biomarkers=[
            SimpleNamespace(name="EGFR", variant="Exon 19 deletion"),
            SimpleNamespace(name="TP53", variant=None),
        ],
        therapy_history=[SimpleNamespace(therapy_name="Osimertinib", therapy_type="targeted therapy")],
        would_consider=["clinical trials"],
        would_not_consider=["long-distance travel without a strong rationale"],
    )


class MatchingServiceTests(unittest.TestCase):
    def test_trial_scoring_uses_normalized_facts(self) -> None:
        profile = build_profile()
        record = ConnectorRecord(
            category="clinical_trials",
            title="EGFR-directed therapy after osimertinib progression",
            source_name="ClinicalTrials.gov",
            source_url="https://clinicaltrials.gov/study/NCT12345678",
            external_identifier="NCT12345678",
            summary="Recruiting study. Phase 1, Phase 2. Conditions: Non-small Cell Lung Cancer. Interventions: Osimertinib (Drug), Amivantamab (Biological). Sites: Dallas, Texas, United States [Recruiting].",
            tags=["Non-small Cell Lung Cancer", "EGFR", "Phase 1", "Phase 2"],
            published_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
            location_summary="UT Southwestern, Dallas, Texas, United States [Recruiting]",
            raw_payload={
                "recruitment_status": "RECRUITING",
                "phases": ["Phase 1", "Phase 2"],
                "conditions": ["Non-small Cell Lung Cancer", "EGFR exon 19 deletion"],
                "interventions": ["Osimertinib (Drug)", "Amivantamab (Biological)"],
                "locations": ["UT Southwestern, Dallas, Texas, United States [Recruiting]"],
                "sponsor": "UT Southwestern",
                "inclusion_excerpt": "Inclusion Criteria: metastatic EGFR exon 19 deletion NSCLC after osimertinib.",
            },
            evidence_label="Eligibility criteria excerpt",
            evidence_snippet="Inclusion Criteria: metastatic EGFR exon 19 deletion NSCLC after osimertinib.",
        )

        match = evaluate(profile, record)

        self.assertGreaterEqual(match.score, 75)
        self.assertEqual(match.relevance_label, "High relevance")
        self.assertIn("biomarker details", " ".join(match.why_it_surfaced).lower())
        self.assertIn("travel area", " ".join(match.why_it_surfaced).lower())
        self.assertEqual(match.normalized_facts["record"]["recruitment_bucket"], "open")
        self.assertIn("record_payload", match.debug)

    def test_closed_mismatch_trial_is_scored_conservatively(self) -> None:
        profile = build_profile()
        record = ConnectorRecord(
            category="clinical_trials",
            title="Completed solid tumor study",
            source_name="ClinicalTrials.gov",
            source_url="https://clinicaltrials.gov/study/NCT99999999",
            external_identifier="NCT99999999",
            summary="Completed study for advanced solid tumors.",
            tags=["solid tumors", "completed"],
            published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
            location_summary="Boston, Massachusetts, United States [Completed]",
            raw_payload={
                "recruitment_status": "COMPLETED",
                "conditions": ["Advanced solid tumors"],
                "locations": ["Boston, Massachusetts, United States [Completed]"],
            },
            evidence_label="Study summary",
            evidence_snippet="Completed study for advanced solid tumors.",
        )

        match = evaluate(profile, record, is_new=False)

        self.assertLess(match.score, 35)
        self.assertEqual(match.relevance_label, "Insufficient data")
        self.assertIn("not currently in an open recruiting status", " ".join(match.why_it_may_not_fit).lower())
