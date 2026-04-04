"""Kick off AI enrichment after ingestion so users get plain-language summaries without a separate step."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import AdminJobRun


def schedule_enrichment_after_ingest(db: Session, *, condition_slug: str, new_items_ingested: int) -> str | None:
    """If configured and OpenAI is available, start ai_enrich_worker in a subprocess.

    Returns the new AdminJobRun id for enrichment, or None if skipped.
    """
    if new_items_ingested <= 0:
        return None
    if not settings.auto_enrich_after_ingest:
        return None
    if not (settings.openai_api_key or "").strip():
        return None

    cap = settings.auto_enrich_max_items
    if cap is None or cap <= 0:
        limit: int | None = None
    else:
        # Enrich at least everything from this ingest batch, even if above the usual cap.
        limit = max(cap, new_items_ingested)

    job = AdminJobRun(
        job_type="ai.enrichment.auto_after_ingest",
        status="running",
        payload_json={"condition_slug": condition_slug, "limit": limit},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    app_dir = Path(__file__).resolve().parents[1]
    script_path = app_dir / "scripts" / "ai_enrich_worker.py"
    backend_root = app_dir.parent
    args = [sys.executable, str(script_path), condition_slug, str(job.id)]
    if limit is not None:
        args.append(str(limit))

    subprocess.Popen(
        args,
        cwd=str(backend_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=sys.platform != "win32",
    )
    return str(job.id)
