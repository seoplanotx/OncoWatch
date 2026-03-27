from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.paths import get_app_paths
from app.models.finding import Finding
from app.models.profile import PatientProfile
from app.models.run import MonitoringRun
from app.models.settings import ReportExport
from app.schemas.run import BriefingSnapshot
from app.services.findings_service import build_briefing_snapshot, rank_findings_for_briefing
from app.utils.dates import utcnow


DISCLAIMER = (
    "OncoWatch is an information monitoring and summarization tool. "
    "It does not determine treatment, trial eligibility, or medical appropriateness. "
    "All findings should be reviewed with a licensed oncology team."
)


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="SectionIntro", parent=styles["BodyText"], textColor=colors.HexColor("#475569")))
    return styles


def _report_title(report_type: str) -> str:
    return "Daily Summary Report" if report_type == "daily_summary" else "Full Oncology Review Report"


def _deterministic_questions(profile: PatientProfile, findings: list[Finding]) -> list[str]:
    questions: list[str] = []
    if profile.biomarkers:
        questions.append("Does the current molecular testing still capture the most important resistance changes to review now?")
    if any(item.type == "clinical_trials" for item in findings):
        questions.append("Are any of these trials worth a formal screening review based on the full chart and current performance status?")
    if profile.current_therapy_status:
        questions.append("Do any of these updates matter for the current treatment plan or the next likely treatment step?")
    if any(item.matching_gaps for item in findings):
        questions.append("Which missing details would matter most before deciding whether any finding is worth pursuing further?")
    questions.append("Should any additional tissue or liquid biopsy work be considered before the next major treatment decision?")
    return questions[:5]


def _profile_rows(profile: PatientProfile) -> list[list[str]]:
    biomarkers = ", ".join(" ".join(filter(None, [b.name, b.variant])) for b in profile.biomarkers) or "—"
    return [
        ["Profile", profile.profile_name],
        ["Display name", profile.display_name or "—"],
        ["Cancer type", profile.cancer_type],
        ["Subtype", profile.subtype or "—"],
        ["Stage / context", profile.stage_or_context or "—"],
        ["Current therapy status", profile.current_therapy_status or "—"],
        ["Location", profile.location_label or "—"],
        ["Travel radius", f"{profile.travel_radius_miles} miles" if profile.travel_radius_miles else "—"],
        ["Biomarkers", biomarkers],
    ]


def _append_profile_snapshot(story: list[Any], styles: Any, profile: PatientProfile) -> None:
    story.append(Paragraph("Patient profile snapshot", styles["SectionTitle"]))
    profile_table = Table(_profile_rows(profile), colWidths=[150, 360])
    profile_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(profile_table)
    story.append(Spacer(1, 12))


def _append_briefing_overview(story: list[Any], styles: Any, briefing: dict[str, Any]) -> None:
    story.append(Paragraph("What changed since last run", styles["SectionTitle"]))

    completed_at = briefing.get("latest_run_completed_at")
    if completed_at is not None:
        story.append(
            Paragraph(
                f"Latest completed run: {completed_at.strftime('%Y-%m-%d %H:%M UTC')}",
                styles["BodySmall"],
            )
        )
    story.append(
        Paragraph(
            f"{briefing.get('new_count', 0)} new findings and {briefing.get('changed_count', 0)} changed findings were prioritized for this briefing.",
            styles["BodyText"],
        )
    )

    blockers = briefing.get("blockers") or []
    overview_rows = [
        ["New findings", str(briefing.get("new_count", 0))],
        ["Changed findings", str(briefing.get("changed_count", 0))],
        ["Confidence blockers", str(len(blockers))],
    ]
    overview_table = Table(overview_rows, colWidths=[220, 80])
    overview_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(Spacer(1, 6))
    story.append(overview_table)
    story.append(Spacer(1, 12))


def _append_finding(story: list[Any], styles: Any, finding: Finding) -> None:
    story.append(Paragraph(finding.title, styles["Heading3"]))
    meta_parts = [finding.source_name, finding.relevance_label, f"Score {finding.score:.1f}"]
    record_facts = (
        finding.match_debug.get("normalized_facts", {}).get("record", {})
        if isinstance(finding.match_debug, dict)
        else {}
    )
    if finding.type == "clinical_trials":
        recruitment_bucket = record_facts.get("recruitment_bucket")
        if recruitment_bucket:
            meta_parts.append(f"Recruitment: {str(recruitment_bucket).replace('_', ' ')}")
    story.append(Paragraph(" • ".join(meta_parts), styles["BodySmall"]))
    story.append(Paragraph(finding.normalized_summary or finding.raw_summary or "No summary available.", styles["BodyText"]))
    if finding.why_it_surfaced:
        story.append(Paragraph(f"<b>Why it surfaced:</b> {finding.why_it_surfaced.replace(chr(10), '; ')}", styles["BodySmall"]))
    if finding.why_it_may_not_fit:
        story.append(Paragraph(f"<b>Why it may not fit:</b> {finding.why_it_may_not_fit.replace(chr(10), '; ')}", styles["BodySmall"]))
    if finding.matching_gaps:
        story.append(Paragraph(f"<b>Missing info:</b> {'; '.join(finding.matching_gaps[:3])}", styles["BodySmall"]))
    story.append(Spacer(1, 6))


def _append_section(story: list[Any], styles: Any, section: dict[str, Any]) -> list[Finding]:
    story.append(Paragraph(section["title"], styles["SectionTitle"]))
    story.append(Paragraph(section["description"], styles["SectionIntro"]))
    story.append(Spacer(1, 4))

    items = section.get("items") or []
    if not items:
        story.append(Paragraph(section["empty_message"], styles["BodyText"]))
        story.append(Spacer(1, 6))
        return []

    for finding in items:
        _append_finding(story, styles, finding)
    return list(items)


def _append_blockers(story: list[Any], styles: Any, blockers: list[dict[str, Any]]) -> None:
    story.append(Paragraph("Confidence blockers / missing info", styles["SectionTitle"]))
    if not blockers:
        story.append(Paragraph("No explicit confidence blockers were stored in the highest-priority findings.", styles["BodyText"]))
        return

    for blocker in blockers:
        examples = blocker.get("examples") or []
        example_text = f" Examples: {', '.join(examples)}." if examples else ""
        story.append(
            Paragraph(
                f"• {blocker['label']} ({blocker['finding_count']} findings).{example_text}",
                styles["BodyText"],
            )
        )


def _append_questions(story: list[Any], styles: Any, profile: PatientProfile, findings: list[Finding]) -> None:
    story.append(Paragraph("Suggested questions for the oncology visit", styles["SectionTitle"]))
    for question in _deterministic_questions(profile, findings):
        story.append(Paragraph(f"• {question}", styles["BodyText"]))


def _append_appendix(story: list[Any], styles: Any, items: list[Finding]) -> None:
    story.append(Paragraph("Evidence appendix", styles["SectionTitle"]))
    for item in items:
        story.append(Paragraph(item.title, styles["Heading3"]))
        story.append(Paragraph(f"Source: {item.source_name}", styles["BodySmall"]))
        if item.source_url:
            story.append(Paragraph(f"URL: {item.source_url}", styles["BodySmall"]))
        if item.evidence_items:
            story.append(Paragraph(item.evidence_items[0].snippet or "No evidence snippet stored.", styles["BodySmall"]))
        story.append(Spacer(1, 4))


def build_report_bytes(
    profile: PatientProfile,
    findings: list[Finding],
    report_type: str,
    *,
    briefing: dict[str, Any],
) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title="OncoWatch Report")
    story: list[Any] = []

    story.append(Paragraph(f"OncoWatch — {_report_title(report_type)}", styles["Title"]))
    story.append(Paragraph(f"Generated: {utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["BodySmall"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(DISCLAIMER, styles["BodySmall"]))
    story.append(Spacer(1, 12))

    _append_briefing_overview(story, styles, briefing)
    _append_profile_snapshot(story, styles, profile)

    appendix_items: list[Finding] = []
    seen_ids: set[int] = set()

    for section in briefing.get("sections", []):
        for finding in _append_section(story, styles, section):
            if finding.id not in seen_ids:
                appendix_items.append(finding)
                seen_ids.add(finding.id)

    _append_blockers(story, styles, briefing.get("blockers", []))
    story.append(Spacer(1, 8))
    _append_questions(story, styles, profile, findings)

    if report_type == "full_review":
        for finding in rank_findings_for_briefing(findings):
            if finding.id not in seen_ids and len(appendix_items) < 20:
                appendix_items.append(finding)
                seen_ids.add(finding.id)

    story.append(Spacer(1, 8))
    _append_appendix(story, styles, appendix_items[:20])

    doc.build(story)
    return buffer.getvalue()


def write_report(session: Session, *, profile: PatientProfile, findings: list[Finding], report_type: str) -> ReportExport:
    latest_run = session.scalar(
        select(MonitoringRun)
        .where(MonitoringRun.profile_id == profile.id)
        .order_by(MonitoringRun.started_at.desc())
    )
    briefing = build_briefing_snapshot(
        findings,
        latest_run=latest_run,
        section_limit=6 if report_type == "daily_summary" else 8,
        blocker_limit=6,
    )
    report_bytes = build_report_bytes(profile, findings, report_type, briefing=briefing)

    paths = get_app_paths()
    timestamp = utcnow().strftime("%Y%m%d-%H%M%S")
    slug = profile.profile_name.lower().replace(" ", "-")
    filename = f"{timestamp}-{report_type}-{slug}.pdf"
    output_path = Path(paths.reports_dir) / filename
    output_path.write_bytes(report_bytes)

    briefing_json = BriefingSnapshot.model_validate(briefing).model_dump(mode="json")
    summary_json = {
        **briefing_json,
        "finding_count": len(findings),
        "profile_name": profile.profile_name,
        "report_title": _report_title(report_type),
        "report_type": report_type,
        "generated_at": utcnow().isoformat(),
    }

    export = ReportExport(
        profile_id=profile.id,
        report_type=report_type,
        status="completed",
        file_path=str(output_path),
        summary_json=summary_json,
    )
    session.add(export)
    session.commit()
    session.refresh(export)
    return export


def can_render_test_pdf() -> tuple[bool, str]:
    try:
        briefing = build_briefing_snapshot([], latest_run=None)
        data = build_report_bytes(
            PatientProfile(
                profile_name="Health Check",
                cancer_type="Demo cancer type",
                subtype="Demo subtype",
                stage_or_context="Demo stage",
                current_therapy_status="Demo status",
                location_label="Local machine",
                would_consider=[],
                would_not_consider=[],
            ),
            [],
            "daily_summary",
            briefing=briefing,
        )
        return (len(data) > 100, "PDF generation ready")
    except Exception as exc:
        return False, f"PDF generation failed: {exc}"


def list_reports(session: Session) -> list[ReportExport]:
    return session.scalars(select(ReportExport).order_by(ReportExport.generated_at.desc())).all()
