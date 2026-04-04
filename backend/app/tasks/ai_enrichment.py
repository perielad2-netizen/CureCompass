from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import AdminJobRun, Condition
from app.services.ai_enrichment_service import AIEnrichmentService
from app.workers.celery_app import celery_app


@celery_app.task(name="ai.enrichment.run_for_condition")
def run_for_condition(condition_slug: str, *, limit: int | None = None, job_id: str | None = None) -> dict:
    db = SessionLocal()
    try:
        cond = db.scalar(select(Condition).where(Condition.slug == condition_slug))
        if not cond:
            raise ValueError(f"Unknown condition slug: {condition_slug}")

        if job_id:
            from uuid import UUID

            job = db.get(AdminJobRun, UUID(job_id))
            if job:
                job.status = "running"
                db.commit()

        service = AIEnrichmentService(db=db)
        stats = service.enrich_condition(cond, limit=limit)

        if job_id:
            from uuid import UUID

            job = db.get(AdminJobRun, UUID(job_id))
            if job:
                job.status = "completed"
                job.output_json = {"stats": stats.__dict__, "condition_slug": condition_slug}
                job.finished_at = datetime.now(tz=timezone.utc)
                db.commit()

        return {"status": "completed", "condition_slug": condition_slug, "stats": stats.__dict__, "job_id": job_id}
    except Exception as exc:  # noqa: BLE001
        if job_id:
            from uuid import UUID

            try:
                job = db.get(AdminJobRun, UUID(job_id))
                if job:
                    job.status = "failed"
                    job.error_text = str(exc)
                    job.finished_at = datetime.now(tz=timezone.utc)
                    job.output_json = {"condition_slug": condition_slug}
                    db.commit()
            except Exception:
                pass
        return {"status": "failed", "condition_slug": condition_slug, "error": str(exc), "job_id": job_id}
    finally:
        db.close()

