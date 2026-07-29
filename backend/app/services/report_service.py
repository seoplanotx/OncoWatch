from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.paths import get_app_paths
from app.core.release import APP_VERSION
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

# Printed in the footer of every page so the caution survives a detached sheet.
FOOTER_DISCLAIMER = "Information monitoring only — review every finding with your oncology team."

# Slate ramp plus one accent, matching the app's palette.
INK = colors.HexColor("#0f172a")
BODY_INK = colors.HexColor("#1e293b")
MUTED = colors.HexColor("#475569")
FAINT = colors.HexColor("#94a3b8")
RULE = colors.HexColor("#cbd5e1")
HAIRLINE = colors.HexColor("#e2e8f0")
TINT = colors.HexColor("#f8fafc")
ACCENT = colors.HexColor("#0f766e")

# Footer occupies y 18..44; header rule sits 46pt below the top edge. Page margins
# below are chosen to clear both.
_FOOTER_RULE_Y = 44.0
_FOOTER_LINE1_Y = 33.0
_FOOTER_LINE2_Y = 21.0
_HEADER_TEXT_DROP = 38.0
_HEADER_RULE_DROP = 46.0

# SimpleDocTemplate builds its Frame with ReportLab's default 6pt padding on every
# side, so flowables sit 6pt inside the declared margins and have 12pt less width
# than doc.width. Declared margins are inset by this so the visible margin is the
# one asked for, and table widths are derived from _content_width, not doc.width.
_FRAME_PADDING = 6.0


def _esc(value: object) -> str:
    """Escape DB text before it reaches a Paragraph.

    ``Paragraph`` parses mini-HTML, so unescaped source text is not merely
    cosmetic: ``?tab=table&rank=1`` renders as ``&rank;=1`` (a corrupted URL) and
    a title containing ``<...>`` loses that span entirely.
    """
    return _xml_escape("" if value is None else str(value))


def _fmt_dt(value: datetime) -> str:
    """Human date/time, UTC — matches the friendlier style of _appointment_line."""
    return f"{value.strftime('%B')} {value.day}, {value.year} at {value.strftime('%H:%M')} UTC"


def _styles() -> StyleSheet1:
    """The report stylesheet, defined outright rather than inherited.

    Deliberately not ``getSampleStyleSheet()``: its Heading3/Heading4 are
    Helvetica-BoldOblique, which is where the old bold-italic item titles came from.
    """
    styles = StyleSheet1()

    def add(name: str, **kwargs: Any) -> None:
        styles.add(ParagraphStyle(name=name, **kwargs))

    add("ReportTitle", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=INK, spaceAfter=2)
    add("ReportMeta", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=MUTED)
    add(
        "AppointmentLine",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=ACCENT,
        spaceBefore=4,
        spaceAfter=2,
    )
    add(
        "SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        textColor=INK,
        spaceBefore=15,
        spaceAfter=3,
    )
    add("SectionIntro", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=MUTED, spaceAfter=4)
    # Plain bold, never BoldOblique: the stock Heading3/Heading4 are italic, which
    # rendered every finding title as bold-italic.
    add("ItemTitle", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=INK, spaceAfter=1)
    add("ItemMeta", fontName="Helvetica", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=2)
    add("Body", fontName="Helvetica", fontSize=9.5, leading=13, textColor=BODY_INK, spaceAfter=3)
    add("BodySmall", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=BODY_INK, spaceAfter=2)
    add("Disclaimer", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED)
    # leftIndent > bulletIndent is what makes wrapped lines hang under the text
    # rather than run back under the bullet.
    add(
        "Bullet",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=BODY_INK,
        leftIndent=14,
        bulletIndent=2,
        spaceAfter=4,
    )
    add(
        "BulletSmall",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=BODY_INK,
        leftIndent=13,
        bulletIndent=2,
        spaceAfter=3,
    )
    # Prep-sheet items are a numbered list: the shared indent keeps the metadata
    # lines aligned under the title rather than under the number.
    add(
        "PrepItemTitle",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12.5,
        textColor=INK,
        leftIndent=17,
        bulletIndent=1,
        spaceAfter=1,
    )
    add(
        "PrepItemMeta",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=MUTED,
        leftIndent=17,
        spaceAfter=1,
    )
    add("KeyLabel", fontName="Helvetica-Bold", fontSize=8.5, leading=11.5, textColor=MUTED)
    add("KeyValue", fontName="Helvetica", fontSize=9, leading=12, textColor=BODY_INK)
    add("StatLabel", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=MUTED)
    add("StatValue", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=INK)
    return styles


def _join_lines(parts: list[str]) -> str:
    """Flatten multi-line reason text onto one line.

    Semicolons are only inserted where a segment does not already end a sentence,
    so stored reasons that come through as full sentences no longer read ".; ".
    """
    joined = ""
    for part in (str(item).strip() for item in parts):
        if not part:
            continue
        if not joined:
            joined = part
        elif joined.endswith((".", "!", "?", ";", ":")):
            joined = f"{joined} {part}"
        else:
            joined = f"{joined}; {part}"
    return joined


def _bullet(text: str, styles: Any, *, style: str = "Bullet") -> Paragraph:
    """A hanging-indent bullet. ``text`` may contain markup; escape data first."""
    return Paragraph(text, styles[style], bulletText="•")


def _section_heading(title: str, styles: Any) -> list[Any]:
    return [
        Paragraph(_esc(title), styles["SectionTitle"]),
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceBefore=0, spaceAfter=5),
    ]


def _draw_page_furniture(
    canvas_obj: Any,
    *,
    page_number: int,
    page_count: int,
    report_title: str,
    context_line: str | None,
    page_width: float,
    page_height: float,
    left_margin: float,
    right_margin: float,
) -> None:
    """Draw the running header and footer for one page.

    Pure drawing against a canvas-like object, so it can be exercised with a stub.
    """
    right_edge = page_width - right_margin

    canvas_obj.saveState()

    # Footer: identity on the left, page position on the right, caution beneath.
    canvas_obj.setStrokeColor(HAIRLINE)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(left_margin, _FOOTER_RULE_Y, right_edge, _FOOTER_RULE_Y)

    canvas_obj.setFont("Helvetica-Bold", 7.5)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawString(left_margin, _FOOTER_LINE1_Y, f"Firstlight — {report_title}")
    canvas_obj.drawRightString(right_edge, _FOOTER_LINE1_Y, f"Page {page_number} of {page_count}")

    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.setFillColor(FAINT)
    canvas_obj.drawString(left_margin, _FOOTER_LINE2_Y, FOOTER_DISCLAIMER)

    # Header on continuation pages only: page 1 already carries the full title block.
    if page_number > 1:
        canvas_obj.setFont("Helvetica-Bold", 7.5)
        canvas_obj.setFillColor(MUTED)
        canvas_obj.drawString(left_margin, page_height - _HEADER_TEXT_DROP, report_title)
        if context_line:
            canvas_obj.setFont("Helvetica", 7.5)
            canvas_obj.setFillColor(FAINT)
            canvas_obj.drawRightString(right_edge, page_height - _HEADER_TEXT_DROP, context_line)
        canvas_obj.setStrokeColor(HAIRLINE)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(
            left_margin,
            page_height - _HEADER_RULE_DROP,
            right_edge,
            page_height - _HEADER_RULE_DROP,
        )

    canvas_obj.restoreState()


def _numbered_canvas(*, report_title: str, context_line: str | None, left_margin: float, right_margin: float):
    """Canvas factory that defers page drawing until the total page count is known."""

    class _NumberedCanvas(pdf_canvas.Canvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._saved_states: list[dict[str, Any]] = []

        def showPage(self) -> None:  # noqa: N802 - ReportLab API
            self._saved_states.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            page_count = len(self._saved_states)
            for state in self._saved_states:
                self.__dict__.update(state)
                width, height = self._pagesize
                _draw_page_furniture(
                    self,
                    page_number=self._pageNumber,
                    page_count=page_count,
                    report_title=report_title,
                    context_line=context_line,
                    page_width=width,
                    page_height=height,
                    left_margin=left_margin,
                    right_margin=right_margin,
                )
                super().showPage()
            self._saved_states = []
            super().save()

    return _NumberedCanvas


def _make_doc(
    buffer: BytesIO,
    *,
    report_title: str,
    side_margin: float,
    top_margin: float,
    bottom_margin: float,
) -> SimpleDocTemplate:
    """A document whose *visible* margins are the ones asked for (see _FRAME_PADDING)."""
    return SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        title=f"Firstlight — {report_title}",
        author="Firstlight",
        subject=report_title,
        creator=f"Firstlight {APP_VERSION}",
        leftMargin=side_margin - _FRAME_PADDING,
        rightMargin=side_margin - _FRAME_PADDING,
        topMargin=top_margin - _FRAME_PADDING,
        bottomMargin=bottom_margin - _FRAME_PADDING,
    )


def _content_width(doc: SimpleDocTemplate) -> float:
    """Width actually available to a flowable, once frame padding is accounted for."""
    return doc.width - 2 * _FRAME_PADDING


_CONTEXT_LINE_LIMIT = 66


def _context_line(profile: PatientProfile) -> str:
    """Clinical context for the running header. No identifying fields.

    Bounded so a verbose stage description cannot grow into the report title on
    the opposite side of the header.
    """
    parts = [profile.cancer_type, profile.subtype, profile.stage_or_context]
    line = " · ".join(part for part in parts if part)
    if len(line) > _CONTEXT_LINE_LIMIT:
        line = f"{line[: _CONTEXT_LINE_LIMIT - 1].rstrip()}…"
    return line


def _kv_table(rows: list[list[str]], *, frame_width: float, styles: Any, label_ratio: float = 0.32) -> Table:
    """Key/value table sized to the frame it lives in and pinned to the left.

    Widths are derived rather than hardcoded, and ``hAlign`` is explicit: ReportLab
    defaults a Table to CENTER, so an over-wide table silently straddles both margins.
    """
    label_width = round(frame_width * label_ratio, 2)
    data = [
        [Paragraph(_esc(label), styles["KeyLabel"]), Paragraph(_esc(value), styles["KeyValue"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=[label_width, frame_width - label_width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), TINT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEABOVE", (0, 0), (-1, 0), 0.6, RULE),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, HAIRLINE),
                ("LINEBELOW", (0, -1), (-1, -1), 0.6, RULE),
            ]
        )
    )
    return table


def _stat_strip(stats: list[tuple[str, str]], *, frame_width: float, styles: Any) -> Table:
    """Counts as a wide label-over-value strip instead of a tall stacked table."""
    column_width = frame_width / len(stats)
    data = [
        [Paragraph(_esc(label.upper()), styles["StatLabel"]) for label, _ in stats],
        [Paragraph(_esc(value), styles["StatValue"]) for _, value in stats],
    ]
    table = Table(data, colWidths=[column_width] * len(stats), hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TINT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("LINEAFTER", (0, 0), (-2, -1), 0.25, HAIRLINE),
            ]
        )
    )
    return table


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


def _append_profile_snapshot(story: list[Any], styles: Any, profile: PatientProfile, *, frame_width: float) -> None:
    story.extend(_section_heading("Patient profile snapshot", styles))
    story.append(_kv_table(_profile_rows(profile), frame_width=frame_width, styles=styles))


def _append_briefing_overview(
    story: list[Any], styles: Any, briefing: dict[str, Any], *, frame_width: float
) -> None:
    story.extend(_section_heading("What changed since last run", styles))

    completed_at = briefing.get("latest_run_completed_at")
    if completed_at is not None:
        story.append(Paragraph(f"Latest completed run: {_fmt_dt(completed_at)}", styles["SectionIntro"]))

    blockers = briefing.get("blockers") or []
    story.append(
        _stat_strip(
            [
                ("New findings", str(briefing.get("new_count", 0))),
                ("Changed findings", str(briefing.get("changed_count", 0))),
                ("Missing-info flags", str(len(blockers))),
            ],
            frame_width=frame_width,
            styles=styles,
        )
    )


def _finding_meta_line(finding: Finding) -> str:
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
    if finding.external_identifier:
        meta_parts.append(finding.external_identifier)
    return " • ".join(_esc(part) for part in meta_parts if part)


def _append_finding(story: list[Any], styles: Any, finding: Finding) -> None:
    # Built as one block so a title never lands at a page bottom with its
    # metadata overleaf.
    block: list[Any] = [
        Paragraph(_esc(finding.title), styles["ItemTitle"]),
        Paragraph(_finding_meta_line(finding), styles["ItemMeta"]),
        Paragraph(
            _esc(finding.normalized_summary or finding.raw_summary or "No summary available."),
            styles["Body"],
        ),
    ]
    if finding.why_it_surfaced:
        block.append(
            Paragraph(
                f"<b>Why it surfaced:</b> {_esc(_join_lines(finding.why_it_surfaced.split(chr(10))))}",
                styles["BodySmall"],
            )
        )
    if finding.why_it_may_not_fit:
        block.append(
            Paragraph(
                f"<b>Why it may not fit:</b> {_esc(_join_lines(finding.why_it_may_not_fit.split(chr(10))))}",
                styles["BodySmall"],
            )
        )
    if finding.matching_gaps:
        block.append(
            Paragraph(
                f"<b>Missing info:</b> {_esc(_join_lines(list(finding.matching_gaps[:3])))}",
                styles["BodySmall"],
            )
        )
    story.append(KeepTogether(block))
    story.append(Spacer(1, 8))


def _append_section(story: list[Any], styles: Any, section: dict[str, Any]) -> list[Finding]:
    story.extend(_section_heading(section["title"], styles))
    story.append(Paragraph(_esc(section["description"]), styles["SectionIntro"]))

    items = section.get("items") or []
    if not items:
        story.append(Paragraph(_esc(section["empty_message"]), styles["Body"]))
        return []

    for finding in items:
        _append_finding(story, styles, finding)
    return list(items)


def _blocker_bullet_text(blocker: dict[str, Any]) -> str:
    """One gap as a single line: the label, then how many findings and which ones.

    Cites identifiers rather than titles — a real oncology title runs 25+ words and
    two of them per bullet buried this section under near-duplicate text.
    """
    count = int(blocker.get("finding_count") or 0)
    suffix = f" — {count} finding{'' if count == 1 else 's'}"
    identifiers = [str(item) for item in (blocker.get("example_identifiers") or []) if item][:2]
    if identifiers:
        suffix += f": {', '.join(identifiers)}"
    return f"{_esc(blocker.get('label'))}<font color=\"#94a3b8\">{_esc(suffix)}</font>"


def _append_blockers(story: list[Any], styles: Any, blockers: list[dict[str, Any]]) -> None:
    story.extend(_section_heading("Information to bring or confirm", styles))
    if not blockers:
        story.append(
            Paragraph("No missing details were flagged on the highest-priority findings.", styles["Body"])
        )
        return

    story.append(Paragraph("Details that would help your team assess fit:", styles["SectionIntro"]))
    for blocker in blockers:
        story.append(_bullet(_blocker_bullet_text(blocker), styles))


def _append_questions(story: list[Any], styles: Any, profile: PatientProfile, findings: list[Finding]) -> None:
    story.extend(_section_heading("Suggested questions for the oncology visit", styles))
    for question in _deterministic_questions(profile, findings):
        story.append(_bullet(_esc(question), styles))


def _append_appendix(story: list[Any], styles: Any, items: list[Finding]) -> None:
    story.extend(_section_heading("Evidence appendix", styles))
    for item in items:
        block: list[Any] = [
            Paragraph(_esc(item.title), styles["ItemTitle"]),
            Paragraph(
                " • ".join(part for part in (_esc(item.source_name), _esc(item.external_identifier)) if part),
                styles["ItemMeta"],
            ),
        ]
        if item.source_url:
            url = _esc(item.source_url)
            block.append(Paragraph(f'<link href="{url}" color="#0f766e">{url}</link>', styles["BodySmall"]))
        if item.evidence_items:
            block.append(
                Paragraph(
                    _esc(item.evidence_items[0].snippet or "No evidence snippet stored."),
                    styles["BodySmall"],
                )
            )
        story.append(KeepTogether(block))
        story.append(Spacer(1, 7))


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
    if finding.user_action == "discuss":
        parts.append("Saved to discuss")
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


def _prep_top_items(findings: list[Finding]) -> list[Finding]:
    """The prep sheet's "Top things to raise": what the user saved leads, ranked;
    the highest-priority remaining items backfill up to the cap.

    Keeps the user's curation meaningful without ever shipping a half-empty sheet.
    Selection stays on top of ``rank_findings_for_briefing`` — the shared ranking
    used by the dashboard is not altered.
    """
    ranked = rank_findings_for_briefing(findings)
    saved = [finding for finding in ranked if finding.user_action == "discuss"]
    rest = [finding for finding in ranked if finding.user_action != "discuss"]
    return (saved + rest)[:APPOINTMENT_PREP_TOP_ITEMS]


def _appointment_line(appointment_date: date | None, appointment_clinician: str | None) -> str | None:
    """Header line naming the visit the prep sheet is for; None when nothing was entered."""
    if appointment_date is None and not appointment_clinician:
        return None
    parts = ["Prepared for the appointment"]
    if appointment_clinician:
        parts.append(f"with {appointment_clinician}")
    if appointment_date is not None:
        parts.append(f"on {appointment_date.strftime('%B')} {appointment_date.day}, {appointment_date.year}")
    return " ".join(parts)


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
        "saved_for_discussion": finding.user_action == "discuss",
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
        top_items = _prep_top_items(findings)
        any_saved = any(item.user_action == "discuss" for item in top_items)
        sections = [
            {
                "key": "top_things_to_raise",
                "title": "Top things to raise",
                "description": (
                    "Your saved-for-discussion items lead, followed by the highest-priority items from your latest check."
                    if any_saved
                    else "The highest-priority items from your latest check."
                ),
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
    appointment_date: date | None = None,
    appointment_clinician: str | None = None,
) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    report_title = _report_title("appointment_prep")
    # Tighter side margins than the long-form reports: this sheet is one-page-first.
    doc = _make_doc(buffer, report_title=report_title, side_margin=52, top_margin=58, bottom_margin=54)
    frame_width = _content_width(doc)
    story: list[Any] = []

    story.append(Paragraph(f"Firstlight — {_esc(report_title)}", styles["ReportTitle"]))
    story.append(Paragraph(f"Generated {_fmt_dt(utcnow())}", styles["ReportMeta"]))
    appointment_line = _appointment_line(appointment_date, appointment_clinician)
    if appointment_line:
        story.append(Paragraph(_esc(appointment_line), styles["AppointmentLine"]))
    # The full disclaimer closes the sheet; a short form rides in the page footer.
    # It used to sit here and consume the top of the page.

    story.extend(_section_heading("Case snapshot", styles))
    story.append(_kv_table(_trimmed_profile_rows(profile), frame_width=frame_width, styles=styles))

    story.extend(_section_heading("Top things to raise", styles))
    top_items = _prep_top_items(findings)
    if not top_items:
        story.append(Paragraph("No monitored findings are stored for this profile yet.", styles["Body"]))
    else:
        for index, finding in enumerate(top_items, start=1):
            status_line = _esc(_prep_finding_status_line(finding))
            if finding.user_action == "discuss":
                status_line = status_line.replace("Saved to discuss", "<b>Saved to discuss</b>")
            block: list[Any] = [
                Paragraph(_esc(finding.title), styles["PrepItemTitle"], bulletText=f"{index}."),
                Paragraph(status_line, styles["PrepItemMeta"]),
            ]
            if finding.why_it_surfaced:
                first_reason = finding.why_it_surfaced.split("\n")[0]
                block.append(
                    Paragraph(
                        f"<b>Why it surfaced:</b> {_esc(first_reason)}",
                        styles["PrepItemMeta"],
                    )
                )
            story.append(KeepTogether(block))
            story.append(Spacer(1, 5))

    story.extend(_section_heading("Questions for your oncology team", styles))
    for question in _deterministic_questions(profile, findings):
        story.append(_bullet(_esc(question), styles, style="BulletSmall"))

    _append_blockers(story, styles, briefing.get("blockers") or [])

    story.append(Spacer(1, 12))
    story.append(Paragraph(_esc(DISCLAIMER), styles["Disclaimer"]))

    doc.build(
        story,
        canvasmaker=_numbered_canvas(
            report_title=report_title,
            context_line=_context_line(profile),
            left_margin=doc.leftMargin + _FRAME_PADDING,
            right_margin=doc.rightMargin + _FRAME_PADDING,
        ),
    )
    return buffer.getvalue()


def build_report_bytes(
    profile: PatientProfile,
    findings: list[Finding],
    report_type: str,
    *,
    briefing: dict[str, Any],
    appointment_date: date | None = None,
    appointment_clinician: str | None = None,
) -> bytes:
    if report_type == "appointment_prep":
        return build_appointment_prep_bytes(
            profile,
            findings,
            briefing=briefing,
            appointment_date=appointment_date,
            appointment_clinician=appointment_clinician,
        )

    styles = _styles()
    buffer = BytesIO()
    report_title = _report_title(report_type)
    doc = _make_doc(buffer, report_title=report_title, side_margin=60, top_margin=58, bottom_margin=54)
    frame_width = _content_width(doc)
    story: list[Any] = []

    story.append(Paragraph(f"Firstlight — {_esc(report_title)}", styles["ReportTitle"]))
    story.append(Paragraph(f"Generated {_fmt_dt(utcnow())}", styles["ReportMeta"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(_esc(DISCLAIMER), styles["Disclaimer"]))

    _append_briefing_overview(story, styles, briefing, frame_width=frame_width)
    _append_profile_snapshot(story, styles, profile, frame_width=frame_width)

    for section in briefing.get("sections", []):
        _append_section(story, styles, section)

    _append_blockers(story, styles, briefing.get("blockers", []))
    _append_questions(story, styles, profile, findings)

    appendix_items = _appendix_items(findings, briefing, report_type)
    if appendix_items:
        # The full review's appendix is back matter; give it its own page.
        if report_type == "full_review":
            story.append(PageBreak())
        _append_appendix(story, styles, appendix_items)

    doc.build(
        story,
        canvasmaker=_numbered_canvas(
            report_title=report_title,
            context_line=_context_line(profile),
            left_margin=doc.leftMargin + _FRAME_PADDING,
            right_margin=doc.rightMargin + _FRAME_PADDING,
        ),
    )
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


def write_report(
    session: Session,
    *,
    profile: PatientProfile,
    findings: list[Finding],
    report_type: str,
    appointment_date: date | None = None,
    appointment_clinician: str | None = None,
) -> ReportExport:
    briefing = _briefing_for(session, profile=profile, findings=findings, report_type=report_type)
    # The appointment details go into the PDF only. They must never reach
    # summary_json or the audit log — the clinician name is identifying.
    report_bytes = build_report_bytes(
        profile,
        findings,
        report_type,
        briefing=briefing,
        appointment_date=appointment_date,
        appointment_clinician=appointment_clinician,
    )

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


def list_reports(session: Session, *, profile_id: int | None = None) -> list[ReportExport]:
    """Report history, newest first.

    With a profile_id, returns that profile's reports plus any whose profile was
    deleted (profile_id SET NULL) — those must stay reachable from every view.
    """
    query = select(ReportExport).order_by(ReportExport.generated_at.desc())
    if profile_id is not None:
        query = query.where((ReportExport.profile_id == profile_id) | (ReportExport.profile_id.is_(None)))
    return session.scalars(query).all()


def count_other_profile_reports(session: Session, *, profile_id: int) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(ReportExport)
            .where(ReportExport.profile_id != profile_id, ReportExport.profile_id.is_not(None))
        )
        or 0
    )


def delete_report(session: Session, report: ReportExport) -> None:
    """Remove one report: the PDF from disk (best-effort) and the history row."""
    report_id, report_type = report.id, report.report_type
    try:
        Path(report.file_path).unlink(missing_ok=True)
    except OSError:
        # A locked or unreachable file must not strand the history row.
        pass
    session.delete(report)
    session.commit()
    record_audit_event("report_deleted", {"report_id": report_id, "report_type": report_type})
