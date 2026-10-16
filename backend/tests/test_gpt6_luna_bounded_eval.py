"""Mocked safety tests for the GPT-6 Luna bounded evaluation harness.

Never calls the live OpenAI API.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
_SCRIPT = _BACKEND / "scripts" / "gpt6_luna_bounded_eval.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("gpt6_luna_bounded_eval", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


harness = _load_harness()


def _valid_ask_ai_json() -> str:
    return json.dumps(
        {
            "direct_answer": "Synthetic answer with clear uncertainty about evidence.",
            "what_changed_recently": "No major indexed updates in the synthetic pool.",
            "evidence_strength": "low",
            "available_now_or_experimental": "unknown / insufficient evidence",
            "suggested_doctor_questions": ["What sources should we review together?"],
            "sources": [
                {
                    "research_item_id": "",
                    "document_id": "",
                    "title": "none",
                    "source_url": "",
                    "published_at": "",
                    "item_type": "paper",
                }
            ],
        }
    )


def _mock_completed_response(*, text: str, model: str = "gpt-6-luna", in_t: int = 100, out_t: int = 50):
    return SimpleNamespace(
        model=model,
        status="completed",
        output_text=text,
        output=[],
        usage=SimpleNamespace(
            input_tokens=in_t,
            output_tokens=out_t,
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )


@pytest.fixture
def prepared(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_RESPONSES_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "none")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE_URL", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    harness.apply_eval_settings()
    scenarios = harness.build_scenarios()
    prepared = []
    for sc in scenarios:
        kwargs = harness.build_request(sc)
        est_in = harness.estimate_request_input_tokens(kwargs)
        est_cost = harness.estimate_cost(est_in, sc.max_output_tokens)
        prepared.append((sc, kwargs, est_in, est_cost))
    return prepared


def test_dry_run_uses_zero_network_requests(monkeypatch: pytest.MonkeyPatch):
    create = MagicMock()

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=create)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-should-not-be-used")
    payload = harness.run_eval(
        execute=False,
        acknowledge=False,
        client_factory=FakeClient,
        write_reports=False,
    )
    assert payload["recommendation"] == "DRY_RUN_PASS"
    assert payload["live_requests"] == 0
    assert create.call_count == 0
    assert all(r["status"] == "dry_run" for r in payload["results"])


def test_missing_api_key_blocks_live(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    payload = harness.run_eval(execute=True, acknowledge=True, write_reports=False)
    assert payload["recommendation"] == "LIVE_BLOCKED"
    assert payload["live_requests"] == 0
    assert any("OPENAI_API_KEY_missing" in g for g in payload["guards"])


def test_missing_acknowledgement_blocks_live(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    payload = harness.run_eval(execute=True, acknowledge=False, write_reports=False)
    assert payload["recommendation"] == "LIVE_BLOCKED"
    assert any("missing_paid_test_acknowledgement" in g for g in payload["guards"])


def test_unexpected_endpoint_blocks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://evil.example/v1")
    payload = harness.run_eval(execute=True, acknowledge=True, write_reports=False)
    assert payload["recommendation"] == "LIVE_BLOCKED"
    assert any("non-official endpoint" in g for g in payload["guards"])
    assert payload["live_requests"] == 0


def test_incorrect_branch_blocks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(harness, "_git", lambda *a: "main" if "branch" in a else "deadbeef")
    monkeypatch.setattr(harness, "_is_ancestor", lambda *a: False)
    monkeypatch.setattr(harness, "core_migration_files_match_baseline", lambda: [])
    payload = harness.run_eval(execute=True, acknowledge=True, write_reports=False)
    assert payload["recommendation"] == "LIVE_BLOCKED"
    assert any("unexpected_branch" in g for g in payload["guards"])


def test_unreviewed_core_migration_blocks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        harness,
        "core_migration_files_match_baseline",
        lambda: ["backend/app/services/openai_responses.py"],
    )
    payload = harness.run_eval(execute=True, acknowledge=True, write_reports=False)
    assert payload["recommendation"] == "LIVE_BLOCKED"
    assert any("core_migration_files_differ" in g for g in payload["guards"])


def test_failed_first_response_stops_all_calls(monkeypatch: pytest.MonkeyPatch, prepared):
    create = MagicMock(side_effect=RuntimeError("boom sk-SECRETVALUE1234567890"))

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs.get("max_retries") == 0
            assert kwargs.get("base_url") == harness.OFFICIAL_OPENAI_BASE
            self.responses = SimpleNamespace(create=create)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(harness, "preflight_guards", lambda **kw: [])
    payload = harness.run_eval(
        execute=True,
        acknowledge=True,
        client_factory=FakeClient,
        write_reports=False,
    )
    assert payload["live_requests"] == 1
    assert create.call_count == 1
    statuses = [r["status"] for r in payload["results"]]
    assert statuses[0] == "fail"
    assert all(s == "skipped" for s in statuses[1:])
    err = payload["results"][0]["error"] or ""
    assert "sk-SECRETVALUE" not in err
    assert err.startswith("provider_error:")


def test_incomplete_response_never_passes(prepared):
    sc, kwargs, _, _ = prepared[0]
    # Ensure models map is populated.
    resp = SimpleNamespace(
        model="gpt-6-luna",
        status="incomplete",
        output_text=_valid_ask_ai_json() if sc.schema_name == "AskAIAnswerOut" else "{}",
        output=[],
        usage=SimpleNamespace(input_tokens=10, output_tokens=10, output_tokens_details=None),
    )
    # For enrichment, incomplete should fail even with parseable text.
    if sc.schema_name != "AskAIAnswerOut":
        # minimal invalid body is fine; status check happens first
        resp.output_text = "{}"
    result = harness.evaluate_response(sc, kwargs, resp, latency_ms=1.0)
    assert result.status == "fail"
    assert result.error == "incomplete_status"
    assert result.incomplete is True


def test_no_usage_data_stops_further_calls(monkeypatch: pytest.MonkeyPatch):
    def _resp(**kwargs):
        return SimpleNamespace(
            model="gpt-6-luna",
            status="completed",
            output_text=_valid_ask_ai_json(),
            output=[],
            usage=None,
        )

    # First scenario may not be AskAI — craft per-call using side_effect with schema-aware text.
    call_count = {"n": 0}

    def create(**kwargs):
        call_count["n"] += 1
        schema_name = kwargs["text"]["format"]["name"]
        # Return completed but missing usage for first call.
        text = "{}"
        if schema_name == "AskAIAnswerOut":
            text = _valid_ask_ai_json()
        elif schema_name == "PrivateDocumentEnrichmentOut":
            text = json.dumps({"patient_summary": "x", "doctor_questions": []})
        return SimpleNamespace(
            model="gpt-6-luna",
            status="completed",
            output_text=text,
            output=[],
            usage=None,
        )

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = SimpleNamespace(create=create)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(harness, "preflight_guards", lambda **kw: [])
    payload = harness.run_eval(
        execute=True,
        acknowledge=True,
        client_factory=FakeClient,
        write_reports=False,
    )
    assert call_count["n"] == 1
    assert payload["live_requests"] == 1
    assert payload["results"][0]["status"] == "fail"
    assert payload["results"][0]["error"] == "usage_missing"
    assert all(r["status"] == "skipped" for r in payload["results"][1:])


def test_budget_exhaustion_stops_before_next_call(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(harness, "preflight_guards", lambda **kw: [])

    # First response spends the entire estimated ceiling; next preflight est cannot fit.
    def fake_run(scenario, kwargs, api_key, client_factory=None):
        return harness.ScenarioResult(
            id=scenario.id,
            title=scenario.title,
            status="pass",
            schema_name=scenario.schema_name,
            input_tokens=10,
            output_tokens=10,
            estimated_cost_usd=harness.SPENDING_CEILING_USD,
            reasoning={"effort": "none"},
        )

    monkeypatch.setattr(harness, "run_scenario_live", fake_run)
    payload = harness.run_eval(execute=True, acknowledge=True, write_reports=False)
    assert payload["live_requests"] == 1
    assert payload["results"][0]["status"] == "pass"
    assert payload["results"][1]["status"] == "skipped"
    assert payload["stop_reason"] == "budget_insufficient_for_next_request"


def test_output_limits_and_eight_request_cap(prepared):
    assert len(prepared) == 8
    total_out = sum(sc.max_output_tokens for sc, _, _, _ in prepared)
    assert total_out == 6600
    for sc, kwargs, _, _ in prepared:
        assert kwargs["max_output_tokens"] == sc.max_output_tokens
        assert kwargs["max_output_tokens"] <= sc.max_output_tokens
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["reasoning"] == {"effort": "none"}


def test_sanitize_provider_errors_redacts_secrets():
    class FakeErr(Exception):
        status_code = 401

    msg = "Incorrect API key provided: sk-ABCDEFGHIJKLMNOPQRSTUV Authorization: Bearer secret-token"
    classified = harness.sanitize_provider_error(FakeErr(msg))
    assert classified == "provider_error:authentication"
    assert "sk-ABCDEF" not in classified
    assert "secret-token" not in classified

    redacted = harness.redact_text(msg)
    assert "sk-ABCDEF" not in redacted
    assert "secret-token" not in redacted
    assert "[REDACTED]" in redacted
    # Bare env-var names must remain readable in operator-facing text.
    assert "OPENAI_API_KEY" in harness.redact_text("missing OPENAI_API_KEY")
    assert "api_key_not_required" in harness.redact_text("api_key_not_required")


def test_complete_valid_response_parses(prepared):
    # Use Ask AI scenario for a known compact schema.
    sc = next(s for s, *_ in prepared if s.schema_name == "AskAIAnswerOut")
    kwargs = next(k for s, k, *_ in prepared if s.id == sc.id)
    resp = _mock_completed_response(text=_valid_ask_ai_json())
    result = harness.evaluate_response(sc, kwargs, resp, latency_ms=12.0)
    assert result.status == "pass"
    assert result.pydantic_ok is True
    assert result.incomplete is False
    assert result.model_returned == "gpt-6-luna"


def test_refusal_fails(prepared):
    sc, kwargs, _, _ = prepared[1]
    resp = SimpleNamespace(
        model="gpt-6-luna",
        status="completed",
        output_text=_valid_ask_ai_json(),
        output=[SimpleNamespace(type="refusal", refusal="no")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1, output_tokens_details=None),
    )
    result = harness.evaluate_response(sc, kwargs, resp, latency_ms=1.0)
    assert result.status == "fail"
    assert result.error == "refusal"


def test_projected_cost_includes_schema_overhead(prepared):
    # Schema-inclusive estimate must exceed prompt-only estimate.
    sc, kwargs, est_in, est_cost = prepared[0]
    prompt_only = harness.estimate_tokens_from_text(sc.system) + harness.estimate_tokens_from_text(sc.user)
    assert est_in > prompt_only
    assert est_cost > 0
    total = sum(c for *_, c in prepared)
    assert total <= harness.SPENDING_CEILING_USD
