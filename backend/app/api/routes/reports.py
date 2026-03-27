from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.report import ReportExportRead, ReportGenerateRequest
from app.services.findings_service import list_findings
from app.services.profile_service import get_active_profile, get_profile
from app.services.report_service import list_reports, write_report

router = APIRouter()


@router.get("", response_model=list[ReportExportRead])
def read_reports(db: Session = Depends(get_db)) -> list[ReportExportRead]:
    return list_reports(db)


@router.post("/generate", response_model=ReportExportRead)
def generate_report(payload: ReportGenerateRequest, db: Session = Depends(get_db)) -> ReportExportRead:
    profile = get_profile(db, payload.profile_id) if payload.profile_id else get_active_profile(db)
    if profile is None:
        raise HTTPException(status_code=400, detail="Create a patient profile first.")
    findings = list_findings(db, profile_id=profile.id)
    return write_report(db, profile=profile, findings=findings, report_type=payload.report_type)


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)) -> FileResponse:
    reports = {report.id: report for report in list_reports(db)}
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(report.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file is missing from disk")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
