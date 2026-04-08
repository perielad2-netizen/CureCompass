import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import AdminJobRun, Condition
from app.services.adapters.clinicaltrials import ClinicalTrialsAdapter
from app.services.adapters.openfda import OpenFDAAdapter
from app.services.adapters.pubmed import PubMedAdapter
from app.services.ingestion_cooldown import touch_ingestion_success
from app.services.ingestion_service import IngestionService
from app.services.post_ingest_enrichment import schedule_enrichment_after_ingest
from app.workers.celery_app import celery_app


@celery_app.task(name="ingestion.run_for_condition")
def run_for_condition(condition_slug: str) -> dict:
    db = SessionLocal()
    try:
        cond = db.scalar(select(Condition).where(Condition.slug == condition_slug))
        if not cond:
            raise ValueError(f"Unknown condition: {condition_slug}")

        job = AdminJobRun(job_type="ingestion.backfill", status="running", payload_json={"condition_slug": condition_slug})
        db.add(job)
        db.commit()
        db.refresh(job)

        adapters = [PubMedAdapter(), ClinicalTrialsAdapter(), OpenFDAAdapter()]
        service = IngestionService(db=db, adapters=adapters)
        result = asyncio.run(service.ingest_for_condition(cond))

        enrichment_job_id = schedule_enrichment_after_ingest(
            db,
            condition_slug=condition_slug,
            new_items_ingested=result.ingested_items,
        )

        job.status = "completed"
        payload = {**result.__dict__}
        if enrichment_job_id:
            payload["enrichment_job_id"] = enrichment_job_id
            payload["enrichment_scheduled"] = True
        else:
            payload["enrichment_scheduled"] = False
        job.output_json = payload
        job.finished_at = datetime.now(tz=timezone.utc)
        db.commit()
        touch_ingestion_success(db, cond.id)
        db.commit()
        return {
            "status": "completed",
            "job_id": str(job.id),
            "result": result.__dict__,
            "enrichment_scheduled": bool(enrichment_job_id),
            "enrichment_job_id": enrichment_job_id,
        }
    except Exception as exc:  # noqa: BLE001
        # Best-effort logging into DB for UI later.
        try:
            db.rollback()
            job = AdminJobRun(job_type="ingestion.backfill", status="failed", payload_json={"condition_slug": condition_slug}, error_text=str(exc))
            db.add(job)
            db.commit()
            db.refresh(job)
            return {"status": "failed", "job_id": str(job.id), "error": str(exc)}
        except Exception:
            return {"status": "failed", "error": str(exc)}
    finally:
        db.close()
