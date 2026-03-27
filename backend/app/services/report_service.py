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
from app.models.settings import ReportExport
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
    return styles


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


def build_report_bytes(profile: PatientProfile, findings: list[Finding], report_type: str) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title="OncoWatch Report")
    story: list[Any] = []

    report_title = "Daily Summary Report" if report_type == "daily_summary" else "Full Oncology Review Report"
    story.append(Paragraph(f"OncoWatch — {report_title}", styles["Title"]))
    story.append(Paragraph(f"Generated: {utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["BodySmall"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(DISCLAIMER, styles["BodySmall"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Patient profile snapshot", styles["SectionTitle"]))
    profile_rows = [
        ["Profile", profile.profile_name],
        ["Display name", profile.display_name or "—"],
        ["Cancer type", profile.cancer_type],
        ["Subtype", profile.subtype or "—"],
        ["Stage / context", profile.stage_or_context or "—"],
        ["Current therapy status", profile.current_therapy_status or "—"],
        ["Location", profile.location_label or "—"],
        ["Travel radius", f"{profile.travel_radius_miles} miles" if profile.travel_radius_miles else "—"],
        ["Biomarkers", ", ".join(" ".join(filter(None, [b.name, b.variant])) for b in profile.biomarkers) or "—"],
    ]
    profile_table = Table(profile_rows, colWidths=[150, 360])
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

    top_items = findings[:8] if report_type == "daily_summary" else findings[:16]
    story.append(Paragraph("Most important new items", styles["SectionTitle"]))
    if not top_items:
        story.append(Paragraph("No findings were stored yet for this profile.", styles["BodyText"]))
    for idx, item in enumerate(top_items, start=1):
        story.append(Paragraph(f"{idx}. {item.title}", styles["Heading3"]))
        story.append(Paragraph(f"{item.source_name} • {item.relevance_label} • Score {item.score}", styles["BodySmall"]))
        story.append(Paragraph(item.normalized_summary or item.raw_summary or "No summary available.", styles["BodyText"]))
        if item.why_it_surfaced:
            story.append(Paragraph(f"<b>Why it surfaced:</b> {item.why_it_surfaced.replace(chr(10), '; ')}", styles["BodySmall"]))
        if item.why_it_may_not_fit:
            story.append(Paragraph(f"<b>Why it may not fit:</b> {item.why_it_may_not_fit.replace(chr(10), '; ')}", styles["BodySmall"]))
        story.append(Spacer(1, 6))

    trial_items = [item for item in findings if item.type == "clinical_trials"][:8]
    story.append(Paragraph("Possible trial matches", styles["SectionTitle"]))
    if not trial_items:
        story.append(Paragraph("No trial-oriented findings are stored yet.", styles["BodyText"]))
    for item in trial_items:
        story.append(Paragraph(item.title, styles["Heading3"]))
        detail = f"{item.source_name} • {item.location_summary or 'Location not listed'} • {item.relevance_label}"
        story.append(Paragraph(detail, styles["BodySmall"]))
        story.append(Paragraph(item.normalized_summary or "No summary available.", styles["BodyText"]))
        story.append(Spacer(1, 4))

    update_items = [item for item in findings if item.type in {"literature", "drug_updates", "biomarker"}][:8]
    story.append(Paragraph("Relevant research / drug updates", styles["SectionTitle"]))
    if not update_items:
        story.append(Paragraph("No research or drug-related findings are stored yet.", styles["BodyText"]))
    for item in update_items:
        story.append(Paragraph(item.title, styles["Heading3"]))
        story.append(Paragraph(f"{item.source_name} • {item.relevance_label}", styles["BodySmall"]))
        story.append(Paragraph(item.normalized_summary or "No summary available.", styles["BodyText"]))
        story.append(Spacer(1, 4))

    missing_info = []
    for item in findings[:10]:
        missing_info.extend(item.matching_gaps)
    story.append(Paragraph("Missing information / data gaps", styles["SectionTitle"]))
    if missing_info:
        for gap in dict.fromkeys(missing_info):
            story.append(Paragraph(f"• {gap}", styles["BodyText"]))
    else:
        story.append(Paragraph("No explicit data gaps were stored in the current findings set.", styles["BodyText"]))

    story.append(Paragraph("Suggested questions for the oncology visit", styles["SectionTitle"]))
    for question in _deterministic_questions(profile, findings):
        story.append(Paragraph(f"• {question}", styles["BodyText"]))

    story.append(Paragraph("Evidence appendix", styles["SectionTitle"]))
    for item in findings[:20]:
        story.append(Paragraph(item.title, styles["Heading3"]))
        story.append(Paragraph(f"Source: {item.source_name}", styles["BodySmall"]))
        if item.source_url:
            story.append(Paragraph(f"URL: {item.source_url}", styles["BodySmall"]))
        if item.evidence_items:
            story.append(Paragraph(item.evidence_items[0].snippet or "No evidence snippet stored.", styles["BodySmall"]))
        story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()


def write_report(session: Session, *, profile: PatientProfile, findings: list[Finding], report_type: str) -> ReportExport:
    report_bytes = build_report_bytes(profile, findings, report_type)
    paths = get_app_paths()
    timestamp = utcnow().strftime("%Y%m%d-%H%M%S")
    slug = profile.profile_name.lower().replace(" ", "-")
    filename = f"{timestamp}-{report_type}-{slug}.pdf"
    output_path = Path(paths.reports_dir) / filename
    output_path.write_bytes(report_bytes)

    export = ReportExport(
        profile_id=profile.id,
        report_type=report_type,
        status="completed",
        file_path=str(output_path),
        summary_json={"finding_count": len(findings)},
    )
    session.add(export)
    session.commit()
    session.refresh(export)
    return export


def can_render_test_pdf() -> tuple[bool, str]:
    try:
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
        )
        return (len(data) > 100, "PDF generation ready")
    except Exception as exc:
        return False, f"PDF generation failed: {exc}"


def list_reports(session: Session) -> list[ReportExport]:
    return session.scalars(select(ReportExport).order_by(ReportExport.generated_at.desc())).all()
