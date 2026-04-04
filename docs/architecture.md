# CureCompass Architecture

## Monorepo layout

- `frontend`: Next.js 15 App Router, TypeScript, Tailwind, Zustand, React Query.
- `backend`: FastAPI, SQLAlchemy 2.x, Alembic, Celery, Redis, adapter-based ingestion.
- `infra`: Docker Compose for Redis (Celery broker); see `docs/ops-redis-celery.md` for worker/Beat.

## Backend modules

- `api/v1/endpoints`: route handlers
- `models`: relational entities
- `services/adapters`: source-specific ingestion adapters
- `services`: ranking, guardrails, AI and retrieval layers
- `tasks` + `workers`: background ingestion and enrichment

## Safety guardrails

- Ask AI must include the current condition in prompt context.
- Disallowed categories are blocked server-side (diagnosis/dosing/emergency).
- UI labels educational-only scope and shows medical disclaimer.
