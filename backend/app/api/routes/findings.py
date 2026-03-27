from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.finding import FindingRead, FindingsQueryResponse
from app.services.findings_service import get_finding, list_findings
from app.services.profile_service import get_active_profile

router = APIRouter()


@router.get("", response_model=FindingsQueryResponse)
def read_findings(
    finding_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    profile_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FindingsQueryResponse:
    if profile_id is None:
        profile = get_active_profile(db)
        profile_id = profile.id if profile else None
    items = list_findings(db, profile_id=profile_id, finding_type=finding_type, q=q)
    return FindingsQueryResponse(total=len(items), items=items)


@router.get("/{finding_id}", response_model=FindingRead)
def read_finding_detail(finding_id: int, db: Session = Depends(get_db)) -> FindingRead:
    finding = get_finding(db, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding
