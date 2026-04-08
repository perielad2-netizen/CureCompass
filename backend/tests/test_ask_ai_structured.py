"""Phase 4 Ask AI: structured schema, trusted_sources builder, backward compatibility."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.ask_ai import AskAIAnswerOut, AskAIStructuredLLMSchema
from app.schemas.medical_intel import NormalizedMedicalDocument
from app.services.ask_ai_structured import (
    build_trusted_sources_from_ranked_evidence,
    intent_structured_guidance,
    merge_structured_into_answer_payload,
)
from app.services.medical_intel.intent import UserIntent


def _norm_doc(
    *,
    title: str,
    url: str,
    source: str = "PubMed",
    entity: str = "research_paper",
    rid: str | None = "550e8400-e29b-41d4-a716-446655440000",
) -> NormalizedMedicalDocument:
    return NormalizedMedicalDocument(
        id="x",
        entity_type=entity,  # type: ignore[arg-type]
        title=title,
        source_name=source,
        source_url=url,
        summary="s",
        plain_language_summary="",
        condition_name="C",
        reliability_score=0.9,
        relevance_score=0.8,
        freshness_score=0.7,
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        raw_data={},
        internal_research_item_id=rid,
    )


def test_legacy_ask_ai_schema_accepts_minimal_payload():
    """Frontend contract: unchanged required fields only."""
    raw = {
        "direct_answer": "a",
        "what_changed_recently": "b",
        "evidence_strength": "c",
        "available_now_or_experimental": "d",
        "suggested_doctor_questions": ["q1"],
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
    m = AskAIAnswerOut.model_validate(raw)
    assert m.direct_answer == "a"


def test_structured_llm_schema_parses_full_json():
    payload = {
        "direct_answer": "da",
        "what_changed_recently": "wc",
        "evidence_strength": "es",
        "available_now_or_experimental": "av",
        "suggested_doctor_questions": ["x"],
        "sources": [
            {
                "research_item_id": "r1",
                "document_id": "",
                "title": "Paper",
                "source_url": "https://example.com",
                "published_at": "",
                "item_type": "research_paper",
            }
        ],
        "simple_explanation": "plain",
        "key_facts": ["f1"],
        "approved_treatments": "at",
        "experimental_or_emerging_options": "ex",
        "relevant_clinical_trials": "ct",
        "warning_signs_or_when_to_seek_care": "ws",
        "what_is_uncertain": "un",
    }
    m = AskAIStructuredLLMSchema.model_validate(payload)
    assert m.simple_explanation == "plain"


def test_structured_schema_rejects_missing_section():
    bad = {
        "direct_answer": "da",
        "what_changed_recently": "wc",
        "evidence_strength": "es",
        "available_now_or_experimental": "av",
        "suggested_doctor_questions": [],
        "sources": [],
        # missing simple_explanation etc.
    }
    with pytest.raises(ValidationError):
        AskAIStructuredLLMSchema.model_validate(bad)


def test_merge_structured_injects_trusted_sources():
    parsed = AskAIStructuredLLMSchema.model_validate(
        {
            "direct_answer": "da",
            "what_changed_recently": "wc",
            "evidence_strength": "es",
            "available_now_or_experimental": "av",
            "suggested_doctor_questions": [],
            "sources": [],
            "simple_explanation": "se",
            "key_facts": [],
            "approved_treatments": "",
            "experimental_or_emerging_options": "",
            "relevant_clinical_trials": "",
            "warning_signs_or_when_to_seek_care": "",
            "what_is_uncertain": "",
        }
    )
    trusted = [{"title": "T", "source_name": "S", "source_url": "u", "short_reason_used": "r"}]
    out = merge_structured_into_answer_payload(parsed, trusted_sources=trusted)
    assert out["trusted_sources"] == trusted
    assert out["simple_explanation"] == "se"
    AskAIAnswerOut.model_validate(out)


def test_trusted_sources_from_aggregated_ranked():
    docs = [_norm_doc(title="A", url="https://a.example")]
    ts = build_trusted_sources_from_ranked_evidence(
        aggregated_ranked_documents=docs,
        research_docs=[],
        used_aggregated_evidence=True,
        private_documents=[],
        mode="research_only",
    )
    assert len(ts) == 1
    assert ts[0]["title"] == "A"
    assert "Ranked evidence" in ts[0]["short_reason_used"]


def test_trusted_sources_fallback_retrieval_order():
    research_docs = [
        {
            "research_item_id": "1",
            "title": "R1",
            "source_url": "https://r",
            "source_name": "PubMed",
            "item_type": "research_paper",
        }
    ]
    ts = build_trusted_sources_from_ranked_evidence(
        aggregated_ranked_documents=None,
        research_docs=research_docs,
        used_aggregated_evidence=False,
        private_documents=[],
        mode="research_only",
    )
    assert ts[0]["source_name"] == "PubMed"


def test_trusted_sources_includes_private_when_mixed_mode():
    ts = build_trusted_sources_from_ranked_evidence(
        aggregated_ranked_documents=None,
        research_docs=[
            {
                "research_item_id": "1",
                "title": "R1",
                "source_url": "https://r",
                "source_name": "PubMed",
                "item_type": "research_paper",
            }
        ],
        used_aggregated_evidence=False,
        private_documents=[("doc-uuid", "myfile.pdf")],
        mode="research_and_documents",
        limit=8,
    )
    assert any(x["source_name"] == "Your uploaded document" for x in ts)


def test_intent_guidance_covers_treatment():
    g = intent_structured_guidance(UserIntent.treatment)
    assert "approved_treatments" in g


def test_fallback_legacy_json_still_validates_as_ask_ai_answer_out():
    """Simulate model failure path: second response is classic only."""
    legacy = {
        "direct_answer": "x",
        "what_changed_recently": "y",
        "evidence_strength": "z",
        "available_now_or_experimental": "w",
        "suggested_doctor_questions": [],
        "sources": [],
    }
    raw = json.dumps(legacy)
    parsed = AskAIAnswerOut.model_validate(json.loads(raw))
    assert "simple_explanation" not in parsed.model_dump()
