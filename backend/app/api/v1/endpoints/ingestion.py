from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import AdminJobRun, Condition, User, UserFollowedCondition
from app.schemas.ingestion import BackfillIn
from app.tasks.ingestion import run_for_condition

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/backfill")
def backfill(
    payload: BackfillIn,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = db.scalar(
        select(Condition).where(Condition.slug == payload.condition_slug)  # type: ignore[name-defined]
    )
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    if not current_user.is_admin:
        followed = db.scalar(
            select(UserFollowedCondition).where(
                UserFollowedCondition.user_id == current_user.id,
                UserFollowedCondition.condition_id == condition.id,
            )
        )
        if not followed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Follow this condition to backfill")

    # In development, Celery runs tasks eagerly (in-process).
    # In production, a Celery worker + Redis will execute this in the background.
    res = run_for_condition.delay(payload.condition_slug)
    # In eager mode this is available immediately.
    try:
        out = res.get(timeout=120)
    except Exception:  # noqa: BLE001
        out = {"status": "queued", "condition_slug": payload.condition_slug}

    return out


@router.get("/jobs/{job_id}")
def get_job(job_id: str, _db=Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        from uuid import UUID

        parsed = UUID(job_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid job id") from exc

    row = _db.get(AdminJobRun, parsed)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not current_user.is_admin:
        condition_slug = row.payload_json.get("condition_slug")
        if not condition_slug:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        condition = _db.scalar(select(Condition).where(Condition.slug == condition_slug))
        if not condition:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        followed = _db.scalar(
            select(UserFollowedCondition).where(
                UserFollowedCondition.user_id == current_user.id,
                UserFollowedCondition.condition_id == condition.id,
            )
        )
        if not followed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return {
        "job_type": row.job_type,
        "status": row.status,
        "payload_json": row.payload_json,
        "output_json": row.output_json,
        "error_text": row.error_text,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }

