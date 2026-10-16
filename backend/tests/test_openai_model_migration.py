"""Focused tests for OpenAI Responses model migration (gpt-6-luna).

Uses mocked OpenAI clients only — never calls the live API.
Settings are patched via scoped monkeypatch so globals restore after each test.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.ai_enrichment import ResearchItemEnrichmentOut
from app.schemas.private_document import PrivateDocumentEnrichmentOut
from app.services import openai_responses as or_mod
from app.services.openai_responses import (
    model_is_legacy_non_reasoning,
    model_supports_responses_reasoning,
    responses_create_kwargs,
    responses_reasoning_param,
    supported_reasoning_efforts,
)


@pytest.fixture
def patch_openai_settings(monkeypatch: pytest.MonkeyPatch):
    """Install a fresh Settings instance on all modules that cache ``settings``."""

    def _apply(**env: str) -> Settings:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        fresh = Settings(_env_file=None)
        monkeypatch.setattr("app.core.config.settings", fresh)
        monkeypatch.setattr("app.services.openai_responses.settings", fresh)
        monkeypatch.setattr("app.services.ai_enrichment_service.settings", fresh)
        monkeypatch.setattr("app.services.private_document_pipeline.settings", fresh)
        monkeypatch.setattr("app.api.v1.endpoints.ask_ai.settings", fresh)
        return fresh

    return _apply


def test_default_responses_model_is_gpt_6_luna():
    s = Settings(_env_file=None)
    assert s.openai_responses_model == "gpt-6-luna"
    assert s.openai_embedding_model == "text-embedding-3-large"
    assert s.openai_reasoning_effort == "none"


def test_env_override_responses_model(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_RESPONSES_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "low")
    s = Settings(_env_file=None)
    assert s.openai_responses_model == "gpt-4.1-mini"
    assert s.openai_reasoning_effort == "low"
    assert s.openai_embedding_model == "text-embedding-3-large"


def test_gpt6_luna_includes_configured_reasoning(patch_openai_settings):
    patch_openai_settings(
        OPENAI_RESPONSES_MODEL="gpt-6-luna",
        OPENAI_REASONING_EFFORT="none",
    )
    kwargs = responses_create_kwargs(
        input=[{"role": "user", "content": "x"}],
        text={"format": {"type": "json_schema", "name": "T", "schema": {}, "strict": True}},
        timeout=90,
    )
    assert kwargs["model"] == "gpt-6-luna"
    assert kwargs["reasoning"] == {"effort": "none"}
    assert kwargs["timeout"] == 90
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["strict"] is True
    assert "temperature" not in kwargs


def test_gpt41_mini_rollback_omits_reasoning(patch_openai_settings):
    """Legacy rollback must not send reasoning (non-reasoning model)."""
    patch_openai_settings(
        OPENAI_RESPONSES_MODEL="gpt-4.1-mini",
        OPENAI_REASONING_EFFORT="none",
    )
    kwargs = responses_create_kwargs(
        input=[{"role": "user", "content": "x"}],
        text={"format": {"type": "json_schema", "name": "T", "schema": {}, "strict": True}},
        timeout=90,
    )
    assert kwargs["model"] == "gpt-4.1-mini"
    assert "reasoning" not in kwargs
    assert kwargs["text"]["format"]["strict"] is True
    assert model_is_legacy_non_reasoning("gpt-4.1-mini")
    assert responses_reasoning_param(model="gpt-4.1-mini") is None


def test_gpt41_mini_snapshot_rollback_omits_reasoning(patch_openai_settings):
    patch_openai_settings(OPENAI_RESPONSES_MODEL="gpt-4.1-mini-2025-04-14")
    kwargs = responses_create_kwargs(
        input=[{"role": "user", "content": "x"}],
        text={"format": {"type": "json_schema", "name": "T", "schema": {}, "strict": True}},
        timeout=60,
    )
    assert kwargs["model"] == "gpt-4.1-mini-2025-04-14"
    assert "reasoning" not in kwargs


def test_unknown_model_override_omits_reasoning(patch_openai_settings):
    """Do not assume unknown models accept reasoning."""
    patch_openai_settings(OPENAI_RESPONSES_MODEL="some-future-model")
    assert model_supports_responses_reasoning("some-future-model") is False
    assert supported_reasoning_efforts("some-future-model") is None
    kwargs = responses_create_kwargs(
        input=[{"role": "user", "content": "x"}],
        text={"format": {"type": "json_schema", "name": "T", "schema": {}, "strict": True}},
        timeout=30,
    )
    assert kwargs["model"] == "some-future-model"
    assert "reasoning" not in kwargs


def test_invalid_reasoning_effort_for_luna_raises(patch_openai_settings):
    patch_openai_settings(
        OPENAI_RESPONSES_MODEL="gpt-6-luna",
        OPENAI_REASONING_EFFORT="ultra",
    )
    with pytest.raises(ValueError, match="Unsupported OPENAI_REASONING_EFFORT"):
        responses_create_kwargs(
            input=[{"role": "user", "content": "x"}],
            text={"format": {"type": "json_schema", "name": "T", "schema": {}, "strict": True}},
            timeout=90,
        )


def test_reasoning_param_normalizes_effort(patch_openai_settings):
    patch_openai_settings(
        OPENAI_RESPONSES_MODEL="gpt-6-luna",
        OPENAI_REASONING_EFFORT="MEDIUM",
    )
    assert responses_reasoning_param() == {"effort": "medium"}


def test_luna_snapshot_supports_reasoning():
    assert model_supports_responses_reasoning("gpt-6-luna-2026-10-01") is True
    assert "none" in (supported_reasoning_efforts("gpt-6-luna-2026-10-01") or set())


def _enrichment_json() -> dict:
    return {
        "lay_summary": "A careful summary of the indexed research paper for patients.",
        "lay_summary_he": "סיכום זהיר של המאמר לחוקרים ולמשפחות בישראל.",
        "clinician_summary": "Clinician-oriented note about study design and limits.",
        "why_it_matters": "Why this update may matter to caregivers.",
        "why_it_matters_he": "למה העדכון עשוי להיות חשוב למשפחות.",
        "evidence_stage": "early_human_study",
        "confidence_level": "low",
        "hype_risk": "promising_but_uncertain",
        "applicability_age_group": "both",
        "availability": "still_experimental",
        "relevance_score": 0.5,
        "novelty_score": 0.5,
        "actionability_score": 0.5,
    }


def test_enrich_one_uses_configured_model_and_parses_json(patch_openai_settings):
    from app.services import ai_enrichment_service as aes

    patch_openai_settings(
        OPENAI_RESPONSES_MODEL="gpt-6-luna",
        OPENAI_REASONING_EFFORT="none",
    )

    payload = _enrichment_json()
    mock_client = MagicMock()
    mock_client.responses.create.return_value = SimpleNamespace(output_text=json.dumps(payload))

    condition = SimpleNamespace(canonical_name="Test Condition")
    item = SimpleNamespace(
        item_type="paper",
        source_url="https://example.com/p",
        published_at=None,
        title="Title",
        abstract_or_body="Abstract body",
    )

    svc = aes.AIEnrichmentService(db=MagicMock())
    svc.client = mock_client
    out = svc.enrich_one(condition, item)  # type: ignore[arg-type]
    assert isinstance(out, ResearchItemEnrichmentOut)
    assert out.lay_summary_he.startswith("סיכום")

    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-6-luna"
    assert call_kwargs["reasoning"] == {"effort": "none"}
    assert call_kwargs["text"]["format"]["type"] == "json_schema"
    assert call_kwargs["text"]["format"]["strict"] is True


def test_enrich_one_legacy_rollback_request_omits_reasoning(patch_openai_settings):
    from app.services import ai_enrichment_service as aes

    patch_openai_settings(OPENAI_RESPONSES_MODEL="gpt-4.1-mini")
    payload = _enrichment_json()
    mock_client = MagicMock()
    mock_client.responses.create.return_value = SimpleNamespace(output_text=json.dumps(payload))

    svc = aes.AIEnrichmentService(db=MagicMock())
    svc.client = mock_client
    condition = SimpleNamespace(canonical_name="C")
    item = SimpleNamespace(
        item_type="paper",
        source_url="u",
        published_at=None,
        title="t",
        abstract_or_body="abstract body text for grounding",
    )
    svc.enrich_one(condition, item)  # type: ignore[arg-type]
    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4.1-mini"
    assert "reasoning" not in call_kwargs
    assert call_kwargs["text"]["format"]["strict"] is True


def test_enrich_one_fails_safely_on_empty_output(patch_openai_settings):
    from app.services import ai_enrichment_service as aes

    patch_openai_settings()
    mock_client = MagicMock()
    mock_client.responses.create.return_value = SimpleNamespace(output_text=None, output=[])

    svc = aes.AIEnrichmentService(db=MagicMock())
    svc.client = mock_client
    condition = SimpleNamespace(canonical_name="C")
    item = SimpleNamespace(
        item_type="paper",
        source_url="u",
        published_at=None,
        title="t",
        abstract_or_body="a",
    )
    with pytest.raises(ValueError, match="No JSON output"):
        svc.enrich_one(condition, item)  # type: ignore[arg-type]


def test_enrich_one_fails_safely_on_malformed_json(patch_openai_settings):
    from app.services import ai_enrichment_service as aes

    patch_openai_settings()
    mock_client = MagicMock()
    mock_client.responses.create.return_value = SimpleNamespace(output_text="{not-json")

    svc = aes.AIEnrichmentService(db=MagicMock())
    svc.client = mock_client
    condition = SimpleNamespace(canonical_name="C")
    item = SimpleNamespace(
        item_type="paper",
        source_url="u",
        published_at=None,
        title="t",
        abstract_or_body="a",
    )
    with pytest.raises(json.JSONDecodeError):
        svc.enrich_one(condition, item)  # type: ignore[arg-type]


def test_private_document_enrichment_uses_model(patch_openai_settings):
    from app.services import private_document_pipeline as pdp

    patch_openai_settings(OPENAI_RESPONSES_MODEL="gpt-6-luna")

    payload = {
        "patient_summary": "Summary of the document.",
        "doctor_questions": ["What does this mean for me?"],
    }
    mock_resp = SimpleNamespace(output_text=json.dumps(payload))
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_resp

    with patch("app.services.private_document_pipeline.OpenAI", return_value=mock_client):
        out = pdp.enrich_document_text(
            text="Lab results: hemoglobin 12.",
            condition_name="Anemia",
            answer_locale="en",
        )
    assert isinstance(out, PrivateDocumentEnrichmentOut)
    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-6-luna"
    assert call_kwargs["reasoning"]["effort"] == "none"


def test_ask_ai_raw_request_contract(patch_openai_settings):
    from app.api.v1.endpoints import ask_ai as ask_mod
    from app.schemas.ask_ai import AskAIAnswerOut

    patch_openai_settings(OPENAI_RESPONSES_MODEL="gpt-6-luna")

    minimal = {
        "direct_answer": "a",
        "what_changed_recently": "b",
        "evidence_strength": "c",
        "available_now_or_experimental": "d",
        "suggested_doctor_questions": ["q"],
        "sources": [
            {
                "research_item_id": "",
                "document_id": "",
                "title": "t",
                "source_url": "",
                "published_at": "",
                "item_type": "paper",
            }
        ],
    }
    mock_client = MagicMock()
    mock_client.responses.create.return_value = SimpleNamespace(output_text=json.dumps(minimal))

    raw = ask_mod._openai_ask_ai_raw(
        mock_client, system="sys", user="user", schema_model=AskAIAnswerOut
    )
    AskAIAnswerOut.model_validate(json.loads(raw))
    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-6-luna"
    assert call_kwargs["reasoning"] == {"effort": "none"}
    assert call_kwargs["text"]["format"]["strict"] is True


def test_settings_restored_after_override(patch_openai_settings):
    """Isolation: patching must not leak into subsequent Settings() defaults."""
    patch_openai_settings(OPENAI_RESPONSES_MODEL="gpt-4.1-mini")
    assert or_mod.settings.openai_responses_model == "gpt-4.1-mini"
    # Fixture teardown happens after this test; next suite tests re-read defaults.


def test_embedding_model_unchanged_in_settings():
    s = Settings(_env_file=None)
    assert s.openai_embedding_model == "text-embedding-3-large"
    assert s.openai_responses_model != s.openai_embedding_model


def test_schema_validation_rejects_incomplete_enrichment():
    with pytest.raises(ValidationError):
        ResearchItemEnrichmentOut.model_validate({"lay_summary": "only"})
