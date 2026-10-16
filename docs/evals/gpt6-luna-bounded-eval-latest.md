# GPT-6 Luna bounded evaluation report

- Generated (UTC): 2026-10-16T08:04:04.837173+00:00
- Mode: `live`
- Branch/SHA: `migrate/openai-gpt-6-luna` / `32a7be983d202d463fc315beac1099358acff6e8`
- Reviewed migration baseline: `f5e57f8160c578411cf49b5e4f0c151f17701721`
- Live requests: 8
- Projected max cost (conservative estimate): $0.004226
- Estimated total cost (usage-based estimate): $0.001500
- Spending ceiling: $0.05
- Recommendation: **PASS**

> Client-side budget guards are estimates, not an absolute OpenAI billing guarantee.

## Safety guards

- Stop on any live failure / refusal / incomplete / invalid JSON / Pydantic failure / unexpected model
- Sanitized provider errors only (no secrets or raw bodies)
- Official OpenAI endpoint only; endpoint env overrides fail closed
- Core migration files must match reviewed baseline SHA
- max_retries=0, max 8 requests, $0.05 estimated ceiling

| Scenario | Status | In/Out/Reason tokens | Est. USD | Notes |
|---|---|---|---|---|
| 1_enrichment Research enrichment (EN + HE fields) | pass | 634/416/0 | 0.000271 |  |
| 2_ask_ai_en Ask AI English | pass | 406/336/0 | 0.000209 |  |
| 3_ask_ai_he Ask AI Hebrew | pass | 409/396/0 | 0.000239 |  |
| 4_condition_resolve Condition resolution | pass | 257/148/0 | 0.000100 |  |
| 5_digest_en English digest | pass | 387/260/0 | 0.000169 |  |
| 6_digest_he Hebrew digest | pass | 384/490/0 | 0.000283 |  |
| 7_private_doc Private document summary | pass | 233/145/0 | 0.000096 |  |
| 8_insufficient_evidence Insufficient evidence / uncertainty | pass | 340/198/0 | 0.000133 |  |

## Guard notes

- branch_and_core_migration_baseline_ok
- ENVIRONMENT_not_production
- official_endpoint_only
- strict_json_schema
- model=gpt-6-luna
- reasoning.effort=none
- no_tools
- projected_max_cost=$0.004226<=0.05
- max_retries=0
- paid_ack
- api_key_present
- stop_on_any_failure
- sanitized_provider_errors
