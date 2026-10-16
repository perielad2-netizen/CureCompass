# OpenAI model migration (CureCompass)

## Summary

| Field | Value |
| --- | --- |
| Previous default Responses model | `gpt-4.1-mini` |
| Replacement | `gpt-6-luna` |
| Embedding model (unchanged) | `text-embedding-3-large` |
| Deprecation / shutdown | GPT-4.1 mini API access ends **2027-01-14** ([deprecations](https://developers.openai.com/api/docs/deprecations)) |
| Official replacement | [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna) |

## Why

OpenAI deprecated GPT-4 series models (including `gpt-4.1-mini`) with shutdown on **January 14, 2027**. The documented recommended replacement is **`gpt-6-luna`**.

## API compatibility decisions

CureCompass already uses the **Responses API** (`client.responses.create`) with **strict JSON Schema** structured outputs (`text.format.type = json_schema`). That path remains the correct integration for GPT-6 Luna:

- Responses API: supported
- Structured outputs: supported
- Chat Completions: not used for these workflows
- Embeddings: still `embeddings.create` with `text-embedding-3-large` (unchanged)

### Reasoning effort

GPT-6 Luna supports `reasoning.effort` values including `none` (default on the model page is `medium`). For latency-sensitive medical JSON workflows (enrichment, Ask AI, digests, private-document summaries, condition resolve), requests send:

```json
"reasoning": { "effort": "none" }
```

Configurable via `OPENAI_REASONING_EFFORT` (default `none`). This approximates prior non-reasoning `gpt-4.1-mini` latency/cost better than leaving the model at medium reasoning.

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
- `backend/app/services/openai_responses.py` — shared Responses kwargs helper
- `backend/app/services/ai_enrichment_service.py`
- `backend/app/api/v1/endpoints/ask_ai.py`
- `backend/app/services/private_document_pipeline.py`
- `backend/app/services/condition_resolve.py`
- `backend/app/services/digest_service.py`
- `backend/tests/test_openai_model_migration.py`
- `docs/OPENAI_MODEL_MIGRATION.md` (this file)

## Production configuration

After deploy (separate approval), set or confirm:

```bash
OPENAI_RESPONSES_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

If production still has `OPENAI_RESPONSES_MODEL=gpt-4.1-mini`, update it before the 2027-01-14 shutdown. Restart API, Celery worker, and Beat after env changes.

## Cost / quality notes (documented pricing, not a live eval)

| | gpt-4.1-mini (legacy) | gpt-6-luna (documented) |
| --- | --- | --- |
| Role | Prior default | Official replacement |
| Input (approx.) | Prior GPT-4.1 mini rates | $0.10 / 1M tokens |
| Output (approx.) | Prior GPT-4.1 mini rates | $0.50 / 1M tokens |
| Reasoning | N/A | Prefer `none` for these flows |

Do **not** treat mocked unit tests as production quality equivalence. Authorize a separate live evaluation on representative enrichment / Ask AI / digest fixtures before claiming production validation.

## Verification (automated)

```bash
cd backend
pytest tests/test_openai_model_migration.py tests/test_ask_ai_structured.py -q
```

Tests mock OpenAI; they do **not** call the live API.

## Rollback

1. Set `OPENAI_RESPONSES_MODEL=gpt-4.1-mini` (only while that model remains available).
2. Restart `curecompass-api`, `curecompass-worker`, `curecompass-beat`.
3. Or revert this branch / redeploy the previous release.

After 2027-01-14, rollback to `gpt-4.1-mini` is not viable; choose another available model if needed.

## Incomplete validations

- No live / paid OpenAI smoke tests in this migration.
- No production env var changes or deploy.
- No rewrite of historical `ResearchItemAI` rows.
