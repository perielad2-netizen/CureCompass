# Redis, Celery worker, and Celery Beat (production)

Background work in CureCompass uses **Celery** with **Redis** as both **message broker** and **result backend**. The API enqueues tasks (ingestion backfill, post-ingest AI enrichment, scheduled digests). A **worker** process executes them; **Beat** schedules recurring digest jobs.

## When tasks run in-process vs in the background

In `app/workers/celery_app.py`, `task_always_eager` is **True** when `ENVIRONMENT=development`. Then `.delay()` runs the task **synchronously inside the API process**—no Redis worker is required for local dev.

For **production**, set `ENVIRONMENT` to something other than `development` (for example `production` or `staging`). Then Celery **requires**:

1. A reachable **Redis** instance (`REDIS_URL`).
2. At least one **Celery worker** subscribed to the `curecompass` queue.
3. A single **Celery Beat** process if you want scheduled research briefings.

Without a worker, `POST /api/ingestion/backfill` and other `.delay()` calls will enqueue work that **never runs**.

## Environment variables

Use the same application settings as the API (same `.env` or secret store). Workers and Beat need **database**, **Redis**, **OpenAI** (for enrichment and digests), and **SMTP** (if digest email delivery is used).

| Variable | Role |
|----------|------|
| `ENVIRONMENT` | Not `development` for async Celery. |
| `REDIS_URL` | Broker + result backend (default `redis://localhost:6379/0`). Use `rediss://` for TLS (e.g. managed Redis). |
| `DATABASE_URL` | SQLAlchemy URL; workers read/write Postgres like the API. |

Optional: use different Redis logical databases for broker vs results by pointing `REDIS_URL` at two URLs—today the app uses one URL for both; that is fine for typical small/medium deployments.

## Redis

- **Managed**: AWS ElastiCache, Redis Cloud, Upstash, Azure Cache, etc. Copy the connection URL into `REDIS_URL`.
- **Self-hosted**: run Redis 7+ (see `infra/docker-compose.yml` for a minimal local/service example).
- Ensure network access from the worker/beat hosts to Redis (security groups, VPC, firewall).

## Celery worker

Run from the **`backend`** directory with the app installed (`pip install -e .`) and virtualenv activated. The Python path must resolve the `app` package (same as running uvicorn).

```bash
cd backend
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
celery -A app.workers.celery_app:celery_app worker -l INFO -Q curecompass
```

- **`-Q curecompass`**: matches `task_default_queue` in `celery_app.py`. Omit only if you use the default queue and have not customized it.
- Scale horizontally by running **multiple worker processes or containers** with the same broker URL (they share the queue).

### Systemd (Linux) sketch

```ini
[Unit]
Description=CureCompass Celery Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/curecompass/backend
EnvironmentFile=/opt/curecompass/backend/.env
ExecStart=/opt/curecompass/backend/.venv/bin/celery -A app.workers.celery_app:celery_app worker -l INFO -Q curecompass
Restart=always

[Install]
WantedBy=multi-user.target
```

Adjust paths, user, and `EnvironmentFile` to your layout.

## Celery Beat

Beat **must run exactly once** per cluster (otherwise the same schedule fires multiple times). It only schedules; workers still execute the tasks.

```bash
cd backend
celery -A app.workers.celery_app:celery_app beat -l INFO
```

### Schedules (UTC)

Defined in `app/workers/celery_app.py`:

| Entry | Task | Schedule |
|-------|------|----------|
| `digest-daily-utc` | `digests.run_scheduled` | Daily 07:00 UTC (`digest_type=daily`) |
| `digest-weekly-utc` | `digests.run_scheduled` | Monday 08:00 UTC (`digest_type=weekly`) |
| `digest-major-utc` | `digests.run_scheduled` | Daily 08:30 UTC (`digest_type=major`) |

Beat persists its last-run state in **`celerybeat-schedule`** (and related files) in the current working directory unless you configure `beat_schedule_filename`. For containers, mount a volume on that path if you need stable state across restarts.

## API process

Run **uvicorn** (or gunicorn + uvicorn workers) as today. It does **not** replace the Celery worker; it only submits tasks.

## Operations checklist (production)

1. Redis up and `REDIS_URL` correct from API, worker, and beat.
2. `ENVIRONMENT` not set to `development` on API and workers.
3. Migrations applied (`alembic upgrade head`) on the database workers use.
4. Worker(s) running with `-Q curecompass`.
5. Single Beat instance running if digests should be automatic.
6. Celery Beat machine clock reasonably accurate (NTP).

## Optional: Flower

For a simple task dashboard:

```bash
pip install flower
celery -A app.workers.celery_app:celery_app flower
```

Run only on protected networks or behind auth.

## Related code

- `app/workers/celery_app.py` — app instance, queue, `beat_schedule`, `task_always_eager`
- `app/tasks/ingestion.py` — backfill
- `app/tasks/ai_enrichment.py` — enrichment
- `app/tasks/digests.py` — scheduled digest generation
