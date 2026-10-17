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

## Bounded synthetic live evaluation harness

Reproducible harness (defaults to **dry-run**; no network):

```bash
cd backend
python scripts/gpt6_luna_bounded_eval.py
```

Mocked safety tests:

```bash
cd backend
pytest tests/test_gpt6_luna_bounded_eval.py -q
```

The bounded live run for this milestone already succeeded (see below). Do not repeat it unless a later PM authorization asks for a new sample.

### Safety guards (live)

| Guard | Behavior |
| --- | --- |
| Branch | Must be `migrate/openai-gpt-6-luna` |
| Reviewed migration baseline | Core app migration files must match SHA `f5e57f8160c578411cf49b5e4f0c151f17701721`; HEAD may be a descendant that only amends harness/docs/tests |
| Endpoint isolation | Fail closed if `OPENAI_BASE_URL` / `OPENAI_API_BASE` / `OPENAI_API_BASE_URL` point away from `https://api.openai.com/v1` |
| Auth / ack | Live requires `OPENAI_API_KEY` and `--i-acknowledge-paid-openai-test` |
| Stop on any failure | Refusal, incomplete status, invalid JSON, Pydantic failure, unexpected model, missing usage, or provider error → no further requests; remaining scenarios marked `skipped` |
| Retries | `max_retries=0` |
| Request cap | Max **8** Responses calls |
| Cost controls | Conservative preflight estimate includes full request serialization + JSON Schema + reserved output tokens + headroom; after each response, usage-based spend updates the running estimate; stop if usage missing, remaining budget insufficient, or observed overspend |
| Spending ceiling | Estimated total **$0.05** (client-side estimate only — **not** an absolute OpenAI billing guarantee) |
| Error sanitization | Reports/console use short classifications only; no API keys, auth headers, request/response bodies, or patient-like content |
| Scope | Synthetic fixtures only; does not modify `backend/.env`; no production DB/SMTP |

Latest concise report: `docs/evals/gpt6-luna-bounded-eval-latest.md`. Prefer updating that file over committing repetitive timestamped dry-run JSON.

## Synthetic live API validation (completed)

**Status: LIVE API VALIDATED** (bounded harness). See production section below for deploy state.

Operator-run bounded live evaluation on 2026-10-16 (report generated `2026-10-16T08:04:04.837173+00:00`). Evidence: `docs/evals/gpt6-luna-bounded-eval-latest.md`.

| Field | Result |
| --- | --- |
| Mode | `live` |
| Recommendation | **PASS** |
| Model / reasoning | `gpt-6-luna` / `none` |
| Branch / SHA | `migrate/openai-gpt-6-luna` / `32a7be983d202d463fc315beac1099358acff6e8` |
| Requests | 8 |
| Passed / failed | 8 / 0 |
| Automated warnings | none |
| Input / output / reasoning tokens | 3050 / 2389 / 0 |
| Usage-based estimated API cost | **$0.001500** |
| Conservative preflight estimate | $0.004226 |
| Estimated spending ceiling | $0.05 (client-side estimate only) |

All eight synthetic scenarios passed with strict JSON Schema / Pydantic validation and no automated warnings:

1. Research enrichment EN+HE — 634 / 416 / 0
2. Ask AI English — 406 / 336 / 0
3. Ask AI Hebrew — 409 / 396 / 0
4. Condition resolution — 257 / 148 / 0
5. English digest — 387 / 260 / 0
6. Hebrew digest — 384 / 490 / 0
7. Private document summarization — 233 / 145 / 0
8. Insufficient evidence / uncertainty — 340 / 198 / 0

This confirms synthetic API compatibility (English and Hebrew structured responses). It is **not** independent medical or editorial review.

No additional live harness runs are required for this milestone. Do not re-run the harness dry-run against this tree if that would overwrite the preserved live report.

## Production deployment (2026-10-16)

**Status: PRODUCTION CODE DEPLOYED** at SHA `9d37425ed29526519cf65f06d8bb3c44cfe21e4f` on VPS path `/opt/CureCompass`.

| Field | Confirmed production state |
| --- | --- |
| Deployed SHA | `9d37425` (`9d37425ed29526519cf65f06d8bb3c44cfe21e4f`) |
| Responses model | `gpt-6-luna` |
| Reasoning effort | `none` |
| Python | 3.12.3 |
| OpenAI Python SDK | 2.30.0 |
| API / Celery worker / Beat | active |
| NRestarts after recovery | 0 |
| Three consecutive API health checks | PASS |
| Recent service errors (post-recovery) | none |
| Database migration for this release | none |
| Frontend deploy for this release | none |

### Permissions incident and recovery (same day)

**Root cause:** the deployment shell used `umask 077` before `git merge --ff-only`. Seven updated Python files were written as `root:root` mode `600`. The `curecompass` service account could not read them. All three backend units failed with `PermissionError` on `app/core/config.py`.

**Recovery:** carefully restored readability on the affected code files (no recursive tree `chmod`/`chown`), validated imports as user `curecompass`, then restarted only the affected CureCompass services. Services recovered; restart counts returned to 0; health checks passed.

**Prevention:** follow the hardened procedure in [deploy-github-linux.md](deploy-github-linux.md) §6 (`umask 022` for Git checkout; keep `.env`/backups private separately; verify readability and offline imports **as the service account** before restart; health probe `http://127.0.0.1:8000/api/health`; rollback via `git switch --detach <GOOD_SHA>`, not backward `merge --ff-only`). Optional read-only helper: `backend/scripts/release_preflight.py` (uses `app.core.config.settings`, not `get_settings`).

### What production verification does and does not mean

| Verified | Not independently completed |
| --- | --- |
| Operational health: units active, health endpoint PASS, no recent post-recovery errors | Production end-to-end **model-response** validation against live user/clinical workflows |
| Configured model / reasoning names as above | Independent **clinical / editorial** review of production answers |
| Pre-merge bounded synthetic live eval (8/8) on an earlier SHA | Re-running paid OpenAI evals in production as part of this hardening doc update |

Operational health ≠ clinical quality sign-off. Human medical / editorial review of real answers remains a separate process. Do not rewrite historical AI rows.

## Remaining follow-ups

- **LIVE API VALIDATED** (bounded synthetic harness) — complete
- **PRODUCTION DEPLOYED** (SHA `9d37425`) — complete after permissions recovery
- Adopt hardened deploy docs / optional `release_preflight.py` on the next maintenance merge
- Clinical / editorial review — **not** independently completed
- Do not rewrite historical AI rows

This documentation update does not perform production SSH, env edits, OpenAI calls, migrations, or service restarts.

## Rollback

1. Set `OPENAI_RESPONSES_MODEL=gpt-4.1-mini` (only while that model remains available). Reasoning is automatically omitted.
2. Restart `curecompass-api`, `curecompass-worker`, `curecompass-beat`.
3. Or revert this branch / redeploy the previous release.

After 2027-01-14, rollback to `gpt-4.1-mini` is not viable; choose another available model if needed.
