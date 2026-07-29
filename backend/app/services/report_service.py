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
from app.services.audit_service import record_audit_event
from app.services.findings_service import build_briefing_snapshot, rank_findings_for_briefing
from app.services.heartbeat_service import deterministic_briefing_questions
from app.utils.dates import utcnow


DISCLAIMER = (
    "Firstlight is an information monitoring and summarization tool. "
    "It does not determine treatment, trial eligibility, or medical appropriateness. "
    "All findings should be reviewed with a licensed oncology team."
)


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="SectionIntro", parent=styles["BodyText"], textColor=colors.HexColor("#475569")))
    return styles


REPORT_TITLES = {
    "daily_summary": "Daily Summary Report",
    "full_review": "Full Oncology Review Report",
    "appointment_prep": "Appointment Prep Sheet",
}


def _report_title(report_type: str) -> str:
    return REPORT_TITLES.get(report_type, "Full Oncology Review Report")


def _deterministic_questions(profile: PatientProfile, findings: list[Finding]) -> list[str]:
    return deterministic_briefing_questions(profile, findings)


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


APPOINTMENT_PREP_TOP_ITEMS = 6
APPENDIX_LIMIT = 20


def _trimmed_profile_rows(profile: PatientProfile) -> list[list[str]]:
    return [row for row in _profile_rows(profile) if row[0] != "Display name" and row[1] not in (None, "", "—")]


def _appendix_items(findings: list[Finding], briefing: dict[str, Any], report_type: str) -> list[Finding]:
    """Findings that land in the evidence appendix, in appendix order."""
    appendix: list[Finding] = []
    seen_ids: set[int] = set()

    for section in briefing.get("sections", []):
        for finding in section.get("items") or []:
            if finding.id not in seen_ids:
                appendix.append(finding)
                seen_ids.add(finding.id)

    if report_type == "full_review":
        for finding in rank_findings_for_briefing(findings):
            if finding.id not in seen_ids and len(appendix) < APPENDIX_LIMIT:
                appendix.append(finding)
                seen_ids.add(finding.id)

    return appendix[:APPENDIX_LIMIT]


def _prep_finding_status_line(finding: Finding) -> str:
    parts: list[str] = []
    status_label = {"new": "New", "changed": "Changed", "unchanged": "Tracked"}.get(finding.status, finding.status.title())
    parts.append(status_label)
    if finding.relevance_label:
        parts.append(finding.relevance_label)
    if finding.external_identifier:
        parts.append(finding.external_identifier)
    record_facts = (
        finding.match_debug.get("normalized_facts", {}).get("record", {})
        if isinstance(finding.match_debug, dict)
        else {}
    )
    if finding.type == "clinical_trials":
        recruitment_bucket = record_facts.get("recruitment_bucket")
        if recruitment_bucket:
            parts.append(f"Recruitment: {str(recruitment_bucket).replace('_', ' ')}")
    return " • ".join(parts)


def _outline_item(finding: Finding) -> dict[str, Any]:
    """One finding reduced to what the in-app report view renders.

    Deliberately carries no identifying fields — the outline is persisted into
    ``ReportExport.summary_json``, which must stay free of patient data.
    """
    first_reason = (finding.why_it_surfaced or "").split("\n")[0].strip()
    return {
        "id": finding.id,
        "title": finding.title,
        "source_name": finding.source_name,
        "source_url": finding.source_url,
        "identifier": finding.external_identifier or "",
        "relevance_label": finding.relevance_label or "",
        "status": finding.status,
        "status_line": _prep_finding_status_line(finding),
        "why_it_surfaced": first_reason or None,
    }


def build_report_outline(
    profile: PatientProfile,
    findings: list[Finding],
    report_type: str,
    *,
    briefing: dict[str, Any],
) -> dict[str, Any]:
    """Describe what a report of this type contains.

    Applies the same caps and ordering the PDF builders apply, so the in-app
    view and the generated PDF cannot drift apart. Used both to preview a
    report before it exists and to render one that already does.
    """
    questions = _deterministic_questions(profile, findings)
    gaps = [
        {
            "label": blocker["label"],
            "finding_count": blocker["finding_count"],
            "examples": list(blocker.get("examples") or []),
        }
        for blocker in (briefing.get("blockers") or [])
    ]

    if report_type == "appointment_prep":
        top_items = rank_findings_for_briefing(findings)[:APPOINTMENT_PREP_TOP_ITEMS]
        sections = [
            {
                "key": "top_things_to_raise",
                "title": "Top things to raise",
                "description": "The highest-priority items from your latest check.",
                "empty_message": "No monitored findings are stored for this profile yet.",
                "count": len(top_items),
                "items": [_outline_item(item) for item in top_items],
            }
        ]
        appendix_count = 0
    else:
        sections = [
            {
                "key": section["key"],
                "title": section["title"],
                "description": section["description"],
                "empty_message": section["empty_message"],
                "count": section["count"],
                "items": [_outline_item(item) for item in section.get("items") or []],
            }
            for section in briefing.get("sections") or []
        ]
        appendix_count = len(_appendix_items(findings, briefing, report_type))

    return {
        "report_type": report_type,
        "report_title": _report_title(report_type),
        "sections": sections,
        "questions": questions,
        "gaps": gaps,
        "counts": {
            "findings": len(findings),
            "new": int(briefing.get("new_count") or 0),
            "changed": int(briefing.get("changed_count") or 0),
            "questions": len(questions),
            "gaps": len(gaps),
            "appendix": appendix_count,
        },
    }


def build_appointment_prep_bytes(
    profile: PatientProfile,
    findings: list[Finding],
    *,
    briefing: dict[str, Any],
) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title="Firstlight Appointment Prep Sheet")
    story: list[Any] = []

    story.append(Paragraph("Firstlight — Appointment Prep Sheet", styles["Title"]))
    story.append(Paragraph(f"Generated: {utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["BodySmall"]))
    story.append(Paragraph(DISCLAIMER, styles["BodySmall"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Case snapshot", styles["SectionTitle"]))
    snapshot_table = Table(_trimmed_profile_rows(profile), colWidths=[150, 360])
    snapshot_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(snapshot_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Top things to raise", styles["SectionTitle"]))
    top_items = rank_findings_for_briefing(findings)[:APPOINTMENT_PREP_TOP_ITEMS]
    if not top_items:
        story.append(Paragraph("No monitored findings are stored for this profile yet.", styles["BodyText"]))
    else:
        for finding in top_items:
            story.append(Paragraph(finding.title, styles["Heading3"]))
            story.append(Paragraph(_prep_finding_status_line(finding), styles["BodySmall"]))
            if finding.why_it_surfaced:
                first_reason = finding.why_it_surfaced.split("\n")[0]
                story.append(Paragraph(f"<b>Why it surfaced:</b> {first_reason}", styles["BodySmall"]))
            story.append(Spacer(1, 6))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Questions for your oncology team", styles["SectionTitle"]))
    for question in _deterministic_questions(profile, findings):
        story.append(Paragraph(f"• {question}", styles["BodyText"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Information to bring or confirm", styles["SectionTitle"]))
    blockers = briefing.get("blockers") or []
    if not blockers:
        story.append(
            Paragraph("No missing details were flagged on the highest-priority findings.", styles["BodyText"])
        )
    else:
        story.append(
            Paragraph(
                "Details that would help your team assess fit:",
                styles["SectionIntro"],
            )
        )
        for blocker in blockers:
            examples = blocker.get("examples") or []
            example_text = f" (e.g. {', '.join(examples)})" if examples else ""
            story.append(Paragraph(f"• {blocker['label']}{example_text}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(DISCLAIMER, styles["BodySmall"]))

    doc.build(story)
    return buffer.getvalue()


def build_report_bytes(
    profile: PatientProfile,
    findings: list[Finding],
    report_type: str,
    *,
    briefing: dict[str, Any],
) -> bytes:
    if report_type == "appointment_prep":
        return build_appointment_prep_bytes(profile, findings, briefing=briefing)

    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title="Firstlight Report")
    story: list[Any] = []

    story.append(Paragraph(f"Firstlight — {_report_title(report_type)}", styles["Title"]))
    story.append(Paragraph(f"Generated: {utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["BodySmall"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(DISCLAIMER, styles["BodySmall"]))
    story.append(Spacer(1, 12))

    _append_briefing_overview(story, styles, briefing)
    _append_profile_snapshot(story, styles, profile)

    for section in briefing.get("sections", []):
        _append_section(story, styles, section)

    _append_blockers(story, styles, briefing.get("blockers", []))
    story.append(Spacer(1, 8))
    _append_questions(story, styles, profile, findings)

    story.append(Spacer(1, 8))
    _append_appendix(story, styles, _appendix_items(findings, briefing, report_type))

    doc.build(story)
    return buffer.getvalue()


def _briefing_for(session: Session, *, profile: PatientProfile, findings: list[Finding], report_type: str) -> dict[str, Any]:
    latest_run = session.scalar(
        select(MonitoringRun)
        .where(MonitoringRun.profile_id == profile.id)
        .order_by(MonitoringRun.started_at.desc())
    )
    return build_briefing_snapshot(
        findings,
        latest_run=latest_run,
        section_limit=6 if report_type == "daily_summary" else 8,
        blocker_limit=6,
    )


def build_report_preview(
    session: Session, *, profile: PatientProfile, findings: list[Finding], report_type: str
) -> dict[str, Any]:
    """The outline a report of this type would have, without rendering or storing anything."""
    briefing = _briefing_for(session, profile=profile, findings=findings, report_type=report_type)
    return build_report_outline(profile, findings, report_type, briefing=briefing)


def write_report(session: Session, *, profile: PatientProfile, findings: list[Finding], report_type: str) -> ReportExport:
    briefing = _briefing_for(session, profile=profile, findings=findings, report_type=report_type)
    report_bytes = build_report_bytes(profile, findings, report_type, briefing=briefing)

    paths = get_app_paths()
    timestamp = utcnow().strftime("%Y%m%d-%H%M%S")
    slug = profile.profile_name.lower().replace(" ", "-")
    filename = f"{timestamp}-{report_type}-{slug}.pdf"
    output_path = Path(paths.reports_dir) / filename
    output_path.write_bytes(report_bytes)

    briefing_json = BriefingSnapshot.model_validate(briefing).model_dump(mode="json")
    # The patient name is intentionally NOT stored in summary_json: it would
    # otherwise sit in plaintext in the database JSON column, defeating the
    # at-rest encryption of identifying fields. The generated PDF still
    # contains the full profile snapshot for the clinician visit.
    summary_json = {
        **briefing_json,
        "finding_count": len(findings),
        "report_title": _report_title(report_type),
        "report_type": report_type,
        "generated_at": utcnow().isoformat(),
        # What this PDF actually contains, so the app can show the report
        # without opening the file. Same no-identifying-data rule applies.
        "outline": build_report_outline(profile, findings, report_type, briefing=briefing),
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
    record_audit_event("report_exported", {"report_id": export.id, "report_type": report_type})
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


def get_report(session: Session, report_id: int) -> ReportExport | None:
    return session.get(ReportExport, report_id)


def list_reports(session: Session) -> list[ReportExport]:
    return session.scalars(select(ReportExport).order_by(ReportExport.generated_at.desc())).all()
