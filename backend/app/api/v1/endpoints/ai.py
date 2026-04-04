import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import AdminJobRun, Condition, User, UserFollowedCondition
from app.schemas.ai_enrichment import EnrichConditionIn

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/enrich")
def enrich_condition(
    payload: EnrichConditionIn,
    _db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = _db.scalar(select(Condition).where(Condition.slug == payload.condition_slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    if not current_user.is_admin:
        followed = _db.scalar(
            select(UserFollowedCondition).where(
                UserFollowedCondition.user_id == current_user.id,
                UserFollowedCondition.condition_id == condition.id,
            )
        )
        if not followed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Follow this condition to enrich its summaries",
            )

    job = AdminJobRun(
        job_type="ai.enrichment.run_for_condition",
        status="running",
        payload_json={"condition_slug": payload.condition_slug, "limit": payload.limit},
    )
    _db.add(job)
    _db.commit()
    _db.refresh(job)

    # In development, spawn a subprocess so the OpenAI calls don't block the API server.
    # (Threads were shown to stall other requests in this environment.)
    if settings.environment == "development":
        this_file = Path(__file__).resolve()
        backend_root = this_file.parents[3].parent  # .../backend
        script_path = this_file.parents[3] / "scripts" / "ai_enrich_worker.py"

        args = [
            sys.executable,
            str(script_path),
            payload.condition_slug,
            str(job.id),
        ]
        if payload.limit is not None:
            args.append(str(payload.limit))

        subprocess.Popen(
            args,
            cwd=str(backend_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    else:
        # In production: you should run this with Celery workers instead.
        # For now, also use subprocess to keep the system functional without extra setup.
        this_file = Path(__file__).resolve()
        backend_root = this_file.parents[3].parent  # .../backend
        script_path = this_file.parents[3] / "scripts" / "ai_enrich_worker.py"
        args = [sys.executable, str(script_path), payload.condition_slug, str(job.id)]
        if payload.limit is not None:
            args.append(str(payload.limit))
        subprocess.Popen(
            args,
            cwd=str(backend_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    return {"status": "queued", "job_id": str(job.id), "condition_slug": payload.condition_slug}

