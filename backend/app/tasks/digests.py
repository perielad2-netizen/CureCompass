from dataclasses import asdict

from app.db.session import SessionLocal
from app.services.digest_service import DigestService
from app.workers.celery_app import celery_app


@celery_app.task(name="digests.run_scheduled")
def run_scheduled(digest_type: str) -> dict:
    db = SessionLocal()
    try:
        svc = DigestService(db)
        stats = svc.run_scheduled(digest_type)
        db.commit()
        return {"status": "ok", "digest_type": digest_type, **asdict(stats)}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return {"status": "failed", "digest_type": digest_type, "error": str(exc)}
    finally:
        db.close()
