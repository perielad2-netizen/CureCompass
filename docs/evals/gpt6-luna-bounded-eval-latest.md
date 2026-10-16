# GPT-6 Luna bounded evaluation report

- Generated (UTC): 2026-10-16T07:38:44.932970+00:00
- Mode: `dry_run`
- Branch/SHA: `migrate/openai-gpt-6-luna` / `083dad399aee38ed7b3b625b8f2bb6254ddbd285`
- Live requests: 0
- Estimated total cost (usage-based estimate): $0.000000
- Spending ceiling: $0.05
- Recommendation: **DRY_RUN_PASS**

> Client-side budget guards are estimates, not an absolute OpenAI billing guarantee.

| Scenario | Status | In/Out/Reason tokens | Est. USD | Notes |
|---|---|---|---|---|
| 1_enrichment Research enrichment (EN + HE fields) | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=1200; preflight_est_input_tokens=319; preflight_est_cost_usd=0.000632 |
| 2_ask_ai_en Ask AI English | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=800; preflight_est_input_tokens=209; preflight_est_cost_usd=0.000421 |
| 3_ask_ai_he Ask AI Hebrew | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=800; preflight_est_input_tokens=201; preflight_est_cost_usd=0.000420 |
| 4_condition_resolve Condition resolution | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=400; preflight_est_input_tokens=90; preflight_est_cost_usd=0.000209 |
| 5_digest_en English digest | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=1200; preflight_est_input_tokens=218; preflight_est_cost_usd=0.000622 |
| 6_digest_he Hebrew digest | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=1200; preflight_est_input_tokens=214; preflight_est_cost_usd=0.000621 |
| 7_private_doc Private document summary | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=600; preflight_est_input_tokens=191; preflight_est_cost_usd=0.000319 |
| 8_insufficient_evidence Insufficient evidence / uncertainty | dry_run | None/None/None | - | keys=['input', 'max_output_tokens', 'model', 'reasoning', 'text', 'timeout']; max_output_tokens=400; preflight_est_input_tokens=129; preflight_est_cost_usd=0.000213 |

## Guard notes

- branch/SHA ok
- ENVIRONMENT not production
- strict json_schema on all requests
- model=gpt-6-luna
- reasoning.effort=none
- no tools
- projected_max_cost=$0.003457 <= $0.05
- dry-run (no network)
- acknowledgement not required for dry-run
- OPENAI_API_KEY not required for dry-run

**Stop reason:** Dry-run only. To execute live: set OPENAI_API_KEY in the shell, then rerun with --execute --i-acknowledge-paid-openai-test

