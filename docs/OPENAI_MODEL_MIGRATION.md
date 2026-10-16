# OpenAI model migration (CureCompass)

## Summary

| Field | Value |
| --- | --- |
| Previous default Responses model | `gpt-4.1-mini` |
| Replacement | `gpt-6-luna` |
| Embedding model (unchanged) | `text-embedding-3-large` |
| Deprecation / shutdown | GPT-4.1 mini API access ends **2027-01-14** ([deprecations](https://developers.openai.com/api/docs/deprecations)) |
| Official replacement | [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| Minimum OpenAI Python SDK | **`openai>=1.66.0`** (Responses API surface) |

## Why

OpenAI deprecated GPT-4 series models (including `gpt-4.1-mini`) with shutdown on **January 14, 2027**. The documented recommended replacement is **`gpt-6-luna`**.

## API compatibility decisions

CureCompass already uses the **Responses API** (`client.responses.create`) with **strict JSON Schema** structured outputs (`text.format.type = json_schema`). That path remains the correct integration for GPT-6 Luna:

- Responses API: supported
- Structured outputs: supported
- Chat Completions: not used for these workflows
- Embeddings: still `embeddings.create` with `text-embedding-3-large` (unchanged)

### Model-aware reasoning

Request construction is **model-aware** in `backend/app/services/openai_responses.py`:

| Model | `reasoning` kwarg |
| --- | --- |
| `gpt-6-luna` / `gpt-6-luna-*` snapshots | Included; `effort` from `OPENAI_REASONING_EFFORT` (default `none`), validated against Luna-supported values: `none`, `low`, `medium`, `high`, `xhigh`, `max` |
| `gpt-4.1-mini` / `gpt-4.1-mini-*` (legacy rollback) | **Omitted** — non-reasoning model; sending `reasoning` may break rollback |
| Unknown / other overrides | **Omitted** — do not assume reasoning support |

Invalid `OPENAI_REASONING_EFFORT` for Luna raises `ValueError` at request-build time (fail closed).

Latency-sensitive medical JSON workflows (enrichment, Ask AI, digests, private-document summaries, condition resolve) use `effort=none` by default for Luna so behavior stays closer to the prior non-reasoning profile than Luna’s documented default of `medium`.

### Legacy model rollback compatibility

To roll back while `gpt-4.1-mini` remains available:

1. Set `OPENAI_RESPONSES_MODEL=gpt-4.1-mini` (optionally leave `OPENAI_REASONING_EFFORT` unchanged; it is ignored for this model).
2. Restart API / worker / beat.
3. Requests keep strict `text.format` JSON Schema and **do not** include `reasoning`.

Automated tests assert both Luna and gpt-4.1-mini request shapes (mocked; no live API).

### SDK compatibility requirements

| Requirement | Decision |
| --- | --- |
| Responses API (`client.responses`) | Introduced in **openai-python 1.66.0** |
| Strict JSON Schema via `text={"format": {...}}` | Responses structured-outputs shape used by this app |
| `reasoning={"effort": ...}` | Supported on Responses for GPT-6 Luna; requires a SDK that exposes the Responses create surface |

`backend/pyproject.toml` lower bound is therefore **`openai>=1.66.0`** (raised from `>=1.45.0`). No unrelated package bumps.

### Preserved behavior

- Environment override: `OPENAI_RESPONSES_MODEL`
- Pydantic validation and API response contracts
- Hebrew + English enrichment / Ask AI / digests
- Medical safety prompts, evidence grounding, citation validation, structured-answer fallback
- Safe failure on empty / malformed model output
- `ResearchItemAI.model_name` records the **current** configured model for **new** enrichments only (historical rows are not rewritten)

## Files updated

- `backend/app/core/config.py` — default model + reasoning effort settings
- `backend/.env.example` — documented env vars
- `backend/app/services/openai_responses.py` — model-aware Responses kwargs helper
- `backend/app/services/ai_enrichment_service.py`
- `backend/app/api/v1/endpoints/ask_ai.py`
- `backend/app/services/private_document_pipeline.py`
- `backend/app/services/condition_resolve.py`
- `backend/app/services/digest_service.py`
- `backend/tests/test_openai_model_migration.py`
- `backend/pyproject.toml` — `openai>=1.66.0`
- `docs/OPENAI_MODEL_MIGRATION.md` (this file)

## Production configuration

After deploy (separate approval), set or confirm:

```bash
OPENAI_RESPONSES_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

Ensure the deployed environment installs `openai>=1.66.0`. Restart API, Celery worker, and Beat after env or dependency changes.

If production still has `OPENAI_RESPONSES_MODEL=gpt-4.1-mini`, update it before the 2027-01-14 shutdown (or keep it only as an intentional temporary rollback).

## Cost / quality notes (documented pricing, not a live eval)

| | gpt-4.1-mini (legacy) | gpt-6-luna (documented) |
| --- | --- | --- |
| Role | Prior default / rollback | Official replacement |
| Input (approx.) | Prior GPT-4.1 mini rates | $0.10 / 1M tokens |
| Output (approx.) | Prior GPT-4.1 mini rates | $0.50 / 1M tokens |
| Reasoning | N/A (parameter omitted) | Prefer `none` for these flows |

Do **not** treat mocked unit tests as production quality equivalence.

## Verification performed (automated)

```bash
cd backend
pytest tests -q
ruff check app/services/openai_responses.py tests/test_openai_model_migration.py
```

Covered with **mocked** OpenAI only:

- Default model / env overrides
- Luna includes validated `reasoning.effort`
- gpt-4.1-mini rollback omits `reasoning` while keeping strict JSON Schema
- Unknown models omit `reasoning`
- Invalid Luna effort fails closed
- Enrichment / Ask AI / private-doc request contracts
- Scoped settings patching (no global settings leak across tests)

## Remaining live validation requirements

- Authorized live smoke: enrichment, Ask AI (HE/EN), digests, private document summarization, structured-answer fallback
- Production env + dependency (`openai>=1.66.0`) confirmation after merge/deploy
- Cost / latency observation under `reasoning.effort=none` on representative traffic

Not done in this PR: live/paid OpenAI calls, production env changes, deploy, DB migrations, historical AI row rewrites.

## Rollback

1. Set `OPENAI_RESPONSES_MODEL=gpt-4.1-mini` (only while that model remains available). Reasoning is automatically omitted.
2. Restart `curecompass-api`, `curecompass-worker`, `curecompass-beat`.
3. Or revert this branch / redeploy the previous release.

After 2027-01-14, rollback to `gpt-4.1-mini` is not viable; choose another available model if needed.
