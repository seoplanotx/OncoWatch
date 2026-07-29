from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from reportlab.platypus import Paragraph
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import AppSettings, Biomarker, Finding, FindingEvidence, MonitoringRun, PatientProfile
from app.services.llm_service import validate_clinician_questions
from app.services.report_service import (
    APPOINTMENT_PREP_TOP_ITEMS,
    FOOTER_DISCLAIMER,
    _appointment_line,
    _blocker_bullet_text,
    _content_width,
    _context_line,
    _draw_page_furniture,
    _esc,
    _join_lines,
    _kv_table,
    _make_doc,
    _prep_top_items,
    _report_title,
    _styles,
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

    def test_prep_top_items_lead_with_saved_findings(self) -> None:
        findings = [
            build_finding(
                profile_id=1,
                monitoring_run_id=1,
                title=f"Trial {index}",
                external_identifier=f"NCT-{index}",
                finding_type="clinical_trials",
                status="new",
                score=95.0 - index,
                relevance_label="High relevance",
                recruitment_bucket="open",
            )
            for index in range(APPOINTMENT_PREP_TOP_ITEMS + 3)
        ]
        # The weakest item by every ranking signal — but the user saved it.
        saved = build_finding(
            profile_id=1,
            monitoring_run_id=1,
            title="Saved literature update",
            external_identifier="LIT-SAVED",
            finding_type="literature",
            status="unchanged",
            score=12.0,
            relevance_label="Worth reviewing",
        )
        saved.user_action = "discuss"
        findings.append(saved)

        top = _prep_top_items(findings)

        self.assertEqual(top[0].external_identifier, "LIT-SAVED")
        self.assertEqual(len(top), APPOINTMENT_PREP_TOP_ITEMS)

    def test_prep_outline_flags_saved_items_and_describes_them(self) -> None:
        profile = build_profile()
        saved = build_finding(
            profile_id=1,
            monitoring_run_id=1,
            title="Saved trial",
            external_identifier="NCT-SAVED",
            finding_type="clinical_trials",
            status="new",
            score=50.0,
            relevance_label="High relevance",
            recruitment_bucket="open",
        )
        saved.user_action = "discuss"
        other = build_finding(
            profile_id=1,
            monitoring_run_id=1,
            title="Unsaved trial",
            external_identifier="NCT-OTHER",
            finding_type="clinical_trials",
            status="new",
            score=90.0,
            relevance_label="High relevance",
            recruitment_bucket="open",
        )
        briefing = {"new_count": 2, "changed_count": 0, "blockers": []}

        outline = build_report_outline(profile, [saved, other], "appointment_prep", briefing=briefing)

        section = outline["sections"][0]
        self.assertEqual(section["items"][0]["identifier"], "NCT-SAVED")
        self.assertTrue(section["items"][0]["saved_for_discussion"])
        self.assertFalse(section["items"][1]["saved_for_discussion"])
        self.assertIn("saved-for-discussion", section["description"])
        self.assertIn("Saved to discuss", section["items"][0]["status_line"])

    def test_appointment_line_formats_optional_parts(self) -> None:
        visit_date = datetime(2026, 8, 5, tzinfo=timezone.utc).date()
        self.assertEqual(
            _appointment_line(visit_date, "Dr. Rivera"),
            "Prepared for the appointment with Dr. Rivera on August 5, 2026",
        )
        self.assertEqual(_appointment_line(None, "Dr. Rivera"), "Prepared for the appointment with Dr. Rivera")
        self.assertEqual(_appointment_line(visit_date, None), "Prepared for the appointment on August 5, 2026")
        self.assertIsNone(_appointment_line(None, None))
        self.assertIsNone(_appointment_line(None, ""))

    def test_appointment_details_render_in_pdf_but_never_persist(self) -> None:
        with self.session_factory() as session:
            profile = build_profile()
            session.add(profile)
            session.commit()
            session.refresh(profile)

            fake_paths = type("Paths", (), {"reports_dir": Path("/virtual/reports")})()
            with patch("app.services.report_service.get_app_paths", return_value=fake_paths):
                with patch("pathlib.Path.write_bytes", return_value=1024):
                    export = write_report(
                        session,
                        profile=profile,
                        findings=[],
                        report_type="appointment_prep",
                        appointment_date=datetime(2026, 8, 5, tzinfo=timezone.utc).date(),
                        appointment_clinician="Dr. Rivera",
                    )

            persisted = json.dumps(export.summary_json)
            self.assertNotIn("Rivera", persisted)
            self.assertNotIn("2026-08-05", persisted)
            self.assertNotIn("August", persisted)

        pdf_bytes = build_report_bytes(
            build_profile(),
            [],
            "appointment_prep",
            briefing={"new_count": 0, "changed_count": 0, "blockers": []},
            appointment_date=datetime(2026, 8, 5, tzinfo=timezone.utc).date(),
            appointment_clinician="Dr. Rivera",
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_appointment_prep_stays_within_two_pages_for_a_full_case(self) -> None:
        profile = build_profile()
        profile.biomarkers = [
            Biomarker(name=f"Biomarker-{index}", variant=f"Variant with a fairly long descriptive name {index}")
            for index in range(6)
        ]
        findings = []
        for index in range(APPOINTMENT_PREP_TOP_ITEMS + 4):
            finding = build_finding(
                profile_id=1,
                monitoring_run_id=1,
                title=(
                    f"Finding {index}: a deliberately long clinical trial title describing the intervention, "
                    "comparator, biomarker population, and phase in the style of a real registry entry"
                ),
                external_identifier=f"NCT-LONG-{index}",
                finding_type="clinical_trials",
                status="new",
                score=90.0 - index,
                relevance_label="High relevance",
                recruitment_bucket="open",
            )
            finding.why_it_surfaced = (
                "Matches the recorded biomarker profile and the current therapy line, and the listed sites fall "
                "inside the configured travel radius for this profile"
            )
            findings.append(finding)
        briefing = {
            "new_count": len(findings),
            "changed_count": 0,
            "blockers": [
                {
                    "label": f"Missing detail {index} that would help confirm fit",
                    "finding_count": 3,
                    "examples": [findings[0].title, findings[1].title],
                }
                for index in range(6)
            ],
        }

        pdf_bytes = build_report_bytes(profile, findings, "appointment_prep", briefing=briefing)

        page_count = pdf_bytes.count(b"/Type /Page") - pdf_bytes.count(b"/Type /Pages")
        self.assertGreaterEqual(page_count, 1)
        self.assertLessEqual(page_count, 2, "appointment prep sheet should stay one-page-first (two max)")

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
        # A light case is the typical case — it must hold the one-page promise.
        self.assertEqual(pdf_bytes.count(b"/Type /Page") - pdf_bytes.count(b"/Type /Pages"), 1)


class ReportFormattingTests(unittest.TestCase):
    """Presentation-layer guarantees: escaping, frame fit, and page furniture."""

    def test_source_text_with_markup_characters_survives_rendering(self) -> None:
        # Paragraph parses mini-HTML, so unescaped source text is corrupted rather
        # than merely ugly: "&rank=1" became "&rank;=1" and "<...>" vanished.
        styles = _styles()
        raw = "Carboplatin & pemetrexed <first-line> in NSCLC ?tab=table&rank=1&aggFilters=status:rec"

        self.assertEqual(Paragraph(_esc(raw), styles["Body"]).getPlainText(), raw)

        unescaped = Paragraph(raw, styles["Body"]).getPlainText()
        self.assertNotEqual(unescaped, raw, "fixture must exercise the characters that break")

    def test_findings_with_markup_characters_render_and_keep_their_text(self) -> None:
        profile = build_profile()
        profile.subtype = "Adenocarcinoma & mixed <NOS>"
        finding = build_finding(
            profile_id=1,
            monitoring_run_id=1,
            title="Osimertinib <plus> bevacizumab & chemotherapy",
            external_identifier="NCT-ESCAPE-1",
            finding_type="clinical_trials",
            status="new",
            score=88.0,
            relevance_label="May be relevant",
            recruitment_bucket="open",
            freshness_bucket="very_recent",
        )
        finding.source_url = "https://clinicaltrials.gov/study/NCT1?tab=table&rank=1&aggFilters=status:rec"
        briefing = {
            "new_count": 1,
            "changed_count": 0,
            "blockers": [],
            "sections": [
                {
                    "key": "new_findings",
                    "title": "New findings",
                    "description": "Items first seen in the latest monitoring cycle.",
                    "empty_message": "None.",
                    "count": 1,
                    "items": [finding],
                }
            ],
        }

        for report_type in ("daily_summary", "full_review", "appointment_prep"):
            with self.subTest(report_type=report_type):
                pdf_bytes = build_report_bytes(profile, [finding], report_type, briefing=briefing)
                self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_key_value_table_fits_its_frame_and_stays_left_aligned(self) -> None:
        # The old tables hardcoded widths totalling 510pt inside a 468pt frame and
        # relied on Table's CENTER default, so they straddled both margins.
        styles = _styles()
        frame_width = 480.0
        table = _kv_table([["Cancer type", "NSCLC"], ["Stage", "IV"]], frame_width=frame_width, styles=styles)

        self.assertEqual(table.hAlign, "LEFT")
        self.assertAlmostEqual(sum(table._argW), frame_width, places=6)

    def test_content_width_accounts_for_reportlab_frame_padding(self) -> None:
        doc = _make_doc(BytesIO(), report_title="Test", side_margin=60, top_margin=58, bottom_margin=54)
        # 612pt Letter minus the 60pt visible margins we asked for.
        self.assertAlmostEqual(_content_width(doc), 612 - 120, places=6)

    def test_page_furniture_draws_identity_page_position_and_caution(self) -> None:
        class StubCanvas:
            def __init__(self) -> None:
                self.strings: list[str] = []
                self.lines: list[tuple[float, float, float, float]] = []
                self.depth = 0

            def saveState(self) -> None:
                self.depth += 1

            def restoreState(self) -> None:
                self.depth -= 1

            def setFont(self, *args: object) -> None: ...

            def setFillColor(self, *args: object) -> None: ...

            def setStrokeColor(self, *args: object) -> None: ...

            def setLineWidth(self, *args: object) -> None: ...

            def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
                self.lines.append((x1, y1, x2, y2))

            def drawString(self, x: float, y: float, text: str) -> None:
                self.strings.append(text)

            def drawRightString(self, x: float, y: float, text: str) -> None:
                self.strings.append(text)

        first = StubCanvas()
        _draw_page_furniture(
            first,
            page_number=1,
            page_count=3,
            report_title="Daily Summary Report",
            context_line="NSCLC · Adenocarcinoma",
            page_width=612,
            page_height=792,
            left_margin=60,
            right_margin=60,
        )
        self.assertIn("Firstlight — Daily Summary Report", first.strings)
        self.assertIn("Page 1 of 3", first.strings)
        self.assertIn(FOOTER_DISCLAIMER, first.strings)
        self.assertEqual(first.depth, 0, "canvas state must be restored")
        # Page 1 carries the full title block, so no running header.
        self.assertNotIn("NSCLC · Adenocarcinoma", first.strings)
        self.assertEqual(len(first.lines), 1)

        later = StubCanvas()
        _draw_page_furniture(
            later,
            page_number=2,
            page_count=3,
            report_title="Daily Summary Report",
            context_line="NSCLC · Adenocarcinoma",
            page_width=612,
            page_height=792,
            left_margin=60,
            right_margin=60,
        )
        self.assertIn("Page 2 of 3", later.strings)
        self.assertIn("NSCLC · Adenocarcinoma", later.strings)
        self.assertEqual(len(later.lines), 2, "continuation pages also rule off the header")

    def test_context_line_is_bounded(self) -> None:
        profile = build_profile()
        profile.stage_or_context = "Stage IV " + "extremely verbose clinical context " * 4
        line = _context_line(profile)
        self.assertLessEqual(len(line), 66)
        self.assertTrue(line.endswith("…"))

    def test_join_lines_does_not_double_up_punctuation(self) -> None:
        self.assertEqual(
            _join_lines(["Eligibility was not evaluated.", "Site may be far."]),
            "Eligibility was not evaluated. Site may be far.",
        )
        self.assertEqual(
            _join_lines(["Matched cancer type", "Matched biomarker"]),
            "Matched cancer type; Matched biomarker",
        )
        self.assertEqual(_join_lines(["  ", "Only one."]), "Only one.")

    def test_blocker_bullets_cite_identifiers_rather_than_full_titles(self) -> None:
        # Two full oncology titles per gap ran to four lines each and buried the
        # section; identifiers are both shorter and directly actionable.
        long_title = "A Phase 3 Randomized Open-Label Study of Amivantamab Plus Lazertinib Versus Chemotherapy"
        text = _blocker_bullet_text(
            {
                "label": "ECOG performance status was not available.",
                "finding_count": 5,
                "examples": [long_title],
                "example_identifiers": ["NCT05388669", "PMID39218447", "NCT04891172"],
            }
        )

        self.assertIn("ECOG performance status was not available.", text)
        self.assertIn("5 findings", text)
        self.assertIn("NCT05388669", text)
        self.assertIn("PMID39218447", text)
        self.assertNotIn("NCT04891172", text, "at most two identifiers keep the bullet on one line")
        self.assertNotIn(long_title, text)

    def test_blocker_bullet_singularises_a_single_finding(self) -> None:
        text = _blocker_bullet_text({"label": "Recent imaging date", "finding_count": 1, "example_identifiers": []})
        self.assertIn("1 finding", text)
        self.assertNotIn("1 findings", text)

    def test_styles_never_use_an_oblique_face(self) -> None:
        # getSampleStyleSheet's Heading3/Heading4 are Helvetica-BoldOblique, which is
        # why every finding title used to render bold-italic.
        styles = _styles()
        for name in styles.byName:
            with self.subTest(style=name):
                self.assertNotIn("Oblique", styles[name].fontName)
                self.assertNotIn("Italic", styles[name].fontName)


if __name__ == "__main__":
    unittest.main()
