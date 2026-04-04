# CureCompass Backend

FastAPI service with PostgreSQL, Redis, Celery workers, and adapter-based ingestion architecture.

## Run (API)

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e .[dev]
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Celery worker and Beat (production)

With `ENVIRONMENT=development`, tasks run **eagerly** in the API process (no worker needed).

For **production**, use Redis plus a worker and (for scheduled digests) Beat. See **[docs/ops-redis-celery.md](../docs/ops-redis-celery.md)** for environment variables, commands, and schedules.

Quick reference (from this directory):

```bash
celery -A app.workers.celery_app:celery_app worker -l INFO -Q curecompass
celery -A app.workers.celery_app:celery_app beat -l INFO
```

Redis only (Docker): `docker compose -f ../infra/docker-compose.yml up -d`
