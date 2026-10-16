# GPT-6 Luna bounded evaluation report

- Generated (UTC): 2026-10-16T07:49:47.978490+00:00
- Mode: `dry_run`
- Branch/SHA: `migrate/openai-gpt-6-luna` / `d4af83b3952fda29f139068aa983e2542f08567f`
- Reviewed migration baseline: `f5e57f8160c578411cf49b5e4f0c151f17701721`
- Live requests: 0
- Projected max cost (conservative estimate): $0.004226
- Estimated total cost (usage-based estimate): $0.000000
- Spending ceiling: $0.05
- Recommendation: **DRY_RUN_PASS**

> Client-side budget guards are estimates, not an absolute OpenAI billing guarantee.

## Safety guards

- Stop on any live failure / refusal / incomplete / invalid JSON / Pydantic failure / unexpected model
- Sanitized provider errors only (no secrets or raw bodies)
- Official OpenAI endpoint only; endpoint env overrides fail closed
- Core migration files must match reviewed baseline SHA
- max_retries=0, max 8 requests, $0.05 estimated ceiling

| Scenario | Status | In/Out/Reason tokens | Est. USD | Notes |
|---|---|---|---|---|
| 1_enrichment Research enrichment (EN + HE fields) | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=1200; preflight_est_input_tokens=1755; preflight_est_cost_usd=0.000775 |
| 2_ask_ai_en Ask AI English | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=800; preflight_est_input_tokens=1235; preflight_est_cost_usd=0.000523 |
| 3_ask_ai_he Ask AI Hebrew | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=800; preflight_est_input_tokens=1220; preflight_est_cost_usd=0.000522 |
| 4_condition_resolve Condition resolution | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=400; preflight_est_input_tokens=826; preflight_est_cost_usd=0.000283 |
| 5_digest_en English digest | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=1200; preflight_est_input_tokens=1218; preflight_est_cost_usd=0.000722 |
| 6_digest_he Hebrew digest | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=1200; preflight_est_input_tokens=1210; preflight_est_cost_usd=0.000721 |
| 7_private_doc Private document summary | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=600; preflight_est_input_tokens=707; preflight_est_cost_usd=0.000371 |
| 8_insufficient_evidence Insufficient evidence / uncertainty | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=400; preflight_est_input_tokens=1090; preflight_est_cost_usd=0.000309 |

## Guard notes

- branch_and_core_migration_baseline_ok
- ENVIRONMENT_not_production
- official_endpoint_only
- strict_json_schema
- model=gpt-6-luna
- reasoning.effort=none
- no_tools
- projected_max_cost=$0.004226<=0.05
- dry_run_no_network
- ack_not_required
- api_key_not_required
- stop_on_any_failure
- sanitized_provider_errors

**Stop reason:** Dry-run only. Live requires OPENAI_API_KEY plus --execute --i-acknowledge-paid-openai-test

