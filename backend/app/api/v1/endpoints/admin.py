from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.entities import AdminJobRun, Source, User
from app.schemas.admin_api import AdminJobRunOut, AdminSourceOut, AdminSourcePatchIn

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs", response_model=list[AdminJobRunOut])
def list_admin_jobs(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
    limit: int = Query(80, ge=1, le=200),
):
    rows = db.scalars(select(AdminJobRun).order_by(AdminJobRun.started_at.desc()).limit(limit)).all()
    return [
        AdminJobRunOut(
            id=str(r.id),
            job_type=r.job_type,
            status=r.status,
            payload_json=r.payload_json or {},
            output_json=r.output_json or {},
            error_text=r.error_text or "",
            started_at=r.started_at,
            finished_at=r.finished_at,
        )
        for r in rows
    ]


@router.get("/sources", response_model=list[AdminSourceOut])
def list_admin_sources(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    rows = db.scalars(select(Source).order_by(Source.name)).all()
    return [
        AdminSourceOut(
            id=str(s.id),
            name=s.name,
            source_type=s.source_type,
            base_url=s.base_url,
            trust_score=s.trust_score,
            enabled=s.enabled,
        )
        for s in rows
    ]


@router.patch("/sources/{source_id}", response_model=AdminSourceOut)
def patch_admin_source(
    source_id: UUID,
    body: AdminSourcePatchIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    row = db.get(Source, source_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    row.enabled = body.enabled
    db.commit()
    db.refresh(row)
    return AdminSourceOut(
        id=str(row.id),
        name=row.name,
        source_type=row.source_type,
        base_url=row.base_url,
        trust_score=row.trust_score,
        enabled=row.enabled,
    )
