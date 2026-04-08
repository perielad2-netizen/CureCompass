"""Phase 4: intent-aware structured-answer prompts and server-built trusted_sources."""

from __future__ import annotations

from app.schemas.ask_ai import AskAIAnswerOut, AskAIStructuredLLMSchema
from app.schemas.medical_intel import NormalizedMedicalDocument
from app.services.medical_intel.intent import UserIntent


def intent_structured_guidance(intent: UserIntent) -> str:
    """Short routing hints for section emphasis (non-exhaustive; model still fills all JSON keys)."""
    m: dict[UserIntent, str] = {
        UserIntent.disease_overview: (
            "Prioritize simple_explanation and key_facts; keep treatment/trial sections short unless the evidence "
            "clearly supports them. Explain any medical terms you use (e.g. benign, mutation, clinical trial phase)."
        ),
        UserIntent.treatment: (
            "Clearly separate approved_treatments (only what regulatory-grade sources in the evidence support) "
            "from experimental_or_emerging_options (trials, early research). If approval status is unclear, "
            "state that in what_is_uncertain."
        ),
        UserIntent.clinical_trials: (
            "Expand relevant_clinical_trials in plain language (what participants do, phases in simple terms). "
            "Do not invent NCT numbers or enrollment."
        ),
        UserIntent.symptoms: (
            "Emphasize warning_signs_or_when_to_seek_care; be calm and practical. Do not diagnose."
        ),
        UserIntent.urgent_warning: (
            "Lead with safety: warning_signs_or_when_to_seek_care and direct_answer must urge appropriate "
            "medical care when red flags may apply. Do not minimize emergencies."
        ),
        UserIntent.drug_info: (
            "Focus approved_treatments / experimental_or_emerging_options on medication context and "
            "warning_signs_or_when_to_seek_care for serious side-effect scenarios. Do not give dosing changes."
        ),
        UserIntent.side_effects: (
            "Prioritize warning_signs_or_when_to_seek_care and what_is_uncertain; tie statements to evidence."
        ),
        UserIntent.latest_research: (
            "Balance key_facts with what_is_uncertain; distinguish peer-reviewed index items from reference snippets."
        ),
    }
    base = m.get(
        intent,
        "Balance all sections; explain jargon briefly; flag uncertainty when evidence is thin.",
    )
    return f"Intent hint ({intent.value}): {base}"


def _reason_line_for_normalized(doc: NormalizedMedicalDocument, rank_index: int) -> str:
    et = doc.entity_type or "item"
    src = (doc.source_name or "source").strip()
    return (
        f"Ranked evidence #{rank_index + 1} ({et}) from {src}, selected for your question after merge/dedupe."
    )


def build_trusted_sources_from_ranked_evidence(
    *,
    aggregated_ranked_documents: list[NormalizedMedicalDocument] | None,
    research_docs: list[dict],
    used_aggregated_evidence: bool,
    private_documents: list[tuple[str, str]],
    mode: str,
    limit: int = 8,
) -> list[dict]:
    """Build trusted_sources for the API from ranked aggregated docs or retrieval order (+ optional uploads).

    ``private_documents`` is (document_id_str, original_filename) for ready user uploads in this request.
    """
    out: list[dict] = []
    if used_aggregated_evidence and aggregated_ranked_documents:
        for i, d in enumerate(aggregated_ranked_documents[:limit]):
            out.append(
                {
                    "title": (d.title or "").strip() or "Untitled",
                    "source_name": (d.source_name or "").strip() or "Unknown source",
                    "source_url": (d.source_url or "").strip(),
                    "short_reason_used": _reason_line_for_normalized(d, i),
                }
            )
    elif mode in ("research_only", "research_and_documents") and research_docs:
        for i, d in enumerate(research_docs[:limit]):
            title = (d.get("title") or "").strip() or "Untitled"
            url = (d.get("source_url") or "").strip()
            src = (d.get("source_name") or d.get("item_type") or "indexed").strip()
            out.append(
                {
                    "title": title,
                    "source_name": src,
                    "source_url": url,
                    "short_reason_used": f"Top trusted-index match #{i + 1} for your question ({src}).",
                }
            )

    if mode in ("documents_only", "research_and_documents") and private_documents:
        for did, name in private_documents:
            if len(out) >= limit:
                break
            out.append(
                {
                    "title": name,
                    "source_name": "Your uploaded document",
                    "source_url": "",
                    "short_reason_used": "Text extracted from your private upload for this condition (not peer-reviewed).",
                }
            )

    return out[:limit]


def merge_structured_into_answer_payload(
    parsed: AskAIStructuredLLMSchema,
    *,
    trusted_sources: list[dict],
) -> dict:
    """Flatten structured LLM output + server trusted_sources into one API/storage dict."""
    base = AskAIAnswerOut.model_validate(parsed.model_dump()).model_dump()
    extra = {
        "simple_explanation": parsed.simple_explanation,
        "key_facts": list(parsed.key_facts),
        "approved_treatments": parsed.approved_treatments,
        "experimental_or_emerging_options": parsed.experimental_or_emerging_options,
        "relevant_clinical_trials": parsed.relevant_clinical_trials,
        "warning_signs_or_when_to_seek_care": parsed.warning_signs_or_when_to_seek_care,
        "what_is_uncertain": parsed.what_is_uncertain,
        "trusted_sources": trusted_sources,
    }
    return {**base, **extra}
