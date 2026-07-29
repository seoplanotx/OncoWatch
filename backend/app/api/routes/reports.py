from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.report import ReportExportRead, ReportGenerateRequest, ReportOutline, ReportType
from app.services.findings_service import list_findings
from app.services.profile_service import get_active_profile, get_profile
from app.services.report_service import build_report_preview, get_report, list_reports, write_report

router = APIRouter()


def _resolve_profile(db: Session, profile_id: int | None):
    profile = get_profile(db, profile_id) if profile_id else get_active_profile(db)
    if profile is None:
        raise HTTPException(status_code=400, detail="Create a patient profile first.")
    return profile


@router.get("", response_model=list[ReportExportRead])
def read_reports(db: Session = Depends(get_db)) -> list[ReportExportRead]:
    return list_reports(db)


@router.get("/preview", response_model=ReportOutline)
def preview_report(
    report_type: ReportType = Query("daily_summary"),
    profile_id: int | None = Query(None),
    db: Session = Depends(get_db),
) -> ReportOutline:
    """What this report would contain. Renders no PDF and stores nothing."""
    profile = _resolve_profile(db, profile_id)
    findings = list_findings(db, profile_id=profile.id)
    return ReportOutline.model_validate(
        build_report_preview(db, profile=profile, findings=findings, report_type=report_type)
    )


@router.post("/generate", response_model=ReportExportRead)
def generate_report(payload: ReportGenerateRequest, db: Session = Depends(get_db)) -> ReportExportRead:
    profile = _resolve_profile(db, payload.profile_id)
    findings = list_findings(db, profile_id=profile.id)
    return write_report(db, profile=profile, findings=findings, report_type=payload.report_type)


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)) -> FileResponse:
    report = get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(report.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file is missing from disk")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
