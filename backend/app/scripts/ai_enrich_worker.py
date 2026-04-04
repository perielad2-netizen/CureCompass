import sys
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import AdminJobRun, Condition
from app.services.ai_enrichment_service import AIEnrichmentService


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: ai_enrich_worker.py <condition_slug> <job_id> [limit]", file=sys.stderr)
        return 2

    condition_slug = sys.argv[1]
    job_id = sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) >= 4 else None

    db = SessionLocal()
    try:
        cond = db.scalar(select(Condition).where(Condition.slug == condition_slug))
        if not cond:
            raise ValueError(f"Unknown condition slug: {condition_slug}")

        job = db.get(AdminJobRun, UUID(job_id))
        if job:
            job.status = "running"
            db.commit()

        service = AIEnrichmentService(db=db)
        stats = service.enrich_condition(cond, limit=limit)

        if job:
            job.status = "completed"
            job.output_json = {"stats": stats.__dict__, "condition_slug": condition_slug}
            job.finished_at = datetime.now(tz=timezone.utc)
            db.commit()

        return 0
    except Exception as exc:  # noqa: BLE001
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
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

