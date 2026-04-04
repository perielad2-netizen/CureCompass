# CureCompass

CureCompass is a condition-focused medical research intelligence platform for patients, caregivers, and families.

This repository contains:

- `frontend`: Next.js App Router web application
- `backend`: FastAPI service, ingestion pipeline, AI enrichment, and API
- `infra`: deployment helpers (e.g. [Redis Compose](infra/docker-compose.yml))
- `docs`: architecture, ADRs, and product/legal docs

## Phase 1 status

Phase 1 scaffolds the production architecture, initial schema, migrations, API shell, and polished first screens.

## Quick start

### Prerequisites

- Node.js 20+
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:3000>  
API docs: <http://localhost:8000/docs>

### Background jobs (Celery + Redis)

Production/staging: run a Celery **worker** and **Beat** (for scheduled digests) against Redis. See [docs/ops-redis-celery.md](docs/ops-redis-celery.md). Local Redis: `docker compose -f infra/docker-compose.yml up -d`.

### GitHub and Linux deployment

See [docs/deploy-github-linux.md](docs/deploy-github-linux.md) for creating the repo, first push, and server setup.
