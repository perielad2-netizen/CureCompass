import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import (
    AskAIConversation,
    AskAIMessage,
    Condition,
    ResearchItem,
    Source,
    User,
    UserFollowedCondition,
    UserPrivateDocument,
)
from app.schemas.ask_ai import AskAIAnswerOut, AskAIIn, AskAIStructuredLLMSchema
from app.schemas.medical_intel import NormalizedMedicalDocument
from app.services.ask_ai_guard import enforce_condition_scope
from app.services.ask_ai_daily_usage import (
    FREE_DAILY_LIMIT_MESSAGE,
    blocked_response_payload,
    can_user_ask_ai,
    increment_successful_ask,
    record_ask_ai_block,
    should_enforce_ask_ai_limit,
    success_usage_extras,
    user_ask_ai_usage_snapshot,
)
from app.services.medical_intel.aggregation import (
    aggregate_and_rank,
    build_legacy_normalized_documents,
    format_aggregated_evidence_for_prompt,
)
from app.services.medical_intel.intent import infer_intent_heuristic
from app.services.medical_intel.orchestrator import (
    fetch_live_normalized_documents,
    fetch_live_reference_block_sync,
)
from app.services.medical_intel.safety import medical_attention_hints
from app.services.ask_ai_structured import (
    build_trusted_sources_from_ranked_evidence,
    intent_structured_guidance,
    merge_structured_into_answer_payload,
)
from app.services.openai_json_schema import patch_json_schema_for_openai_strict
from app.services.private_document_pipeline import build_private_context_chunks
from app.services.retrieval import RetrievalService

router = APIRouter(tags=["ask-ai"])
_ask_ai_log = logging.getLogger(__name__)


def _ask_ai_schema_text_config(schema_model: type[BaseModel]) -> dict:
    schema = schema_model.model_json_schema()
    patch_json_schema_for_openai_strict(schema)

    return {
        "format": {
            "type": "json_schema",
            "name": schema_model.__name__,
            "schema": schema,
            "strict": True,
        }
    }


def _openai_ask_ai_raw(client: OpenAI, *, system: str, user: str, schema_model: type[BaseModel]) -> str:
    response = client.responses.create(
        model=settings.openai_responses_model,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        text=_ask_ai_schema_text_config(schema_model),
        timeout=90,
    )
    raw = getattr(response, "output_text", None)
    if not raw:
        try:
            raw = response.output[0].content[0].text  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Ask AI output parsing failed: {exc}") from exc
    return raw


def _research_unavailable_detail(db: Session, condition_id: UUID) -> str:
    n_any = db.scalar(select(func.count()).select_from(ResearchItem).where(ResearchItem.condition_id == condition_id))
    n_trusted = db.scalar(
        select(func.count())
        .select_from(ResearchItem)
        .join(Source, Source.id == ResearchItem.source_id)
        .where(ResearchItem.condition_id == condition_id, Source.trust_score >= 0.8)
    )
    if (n_any or 0) == 0:
        return (
            "There are no indexed research items for this condition yet, so Ask AI has nothing to search. "
            "Use “Check for updates” on your dashboard (or run ingestion) to pull records from PubMed, "
            "ClinicalTrials.gov, and openFDA. Ask AI only answers from those trusted indexed sources."
        )
    return (
        f"This condition has {n_any} indexed item(s), but none are attached to a source with trust score ≥ 0.8, "
        "which Ask AI requires. Re-seed sources (PubMed, ClinicalTrials.gov, openFDA) or fix Source.trust_score in the database."
    )


def _load_private_documents(
    db: Session,
    *,
    user_id: UUID,
    condition_id: UUID,
    document_ids: list[str],
) -> list[UserPrivateDocument]:
    q = select(UserPrivateDocument).where(
        UserPrivateDocument.user_id == user_id,
        UserPrivateDocument.condition_id == condition_id,
        UserPrivateDocument.processing_status == "ready",
    )
    if document_ids:
        want: list[UUID] = []
        for s in document_ids:
            try:
                want.append(UUID(s))
            except ValueError:
                continue
        if not want:
            return []
        q = q.where(UserPrivateDocument.id.in_(want))
    return list(db.scalars(q).all())


@router.post("/conditions/{slug}/ask-ai")
def ask_ai(
    slug: str,
    payload: AskAIIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    follow = db.scalar(
        select(UserFollowedCondition).where(
            UserFollowedCondition.user_id == current_user.id,
            UserFollowedCondition.condition_id == condition.id,
        )
    )
    if not follow:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Follow this condition to use Ask AI.")

    enforce_condition_scope(payload.prompt, condition.canonical_name)

    if should_enforce_ask_ai_limit(current_user):
        if not can_user_ask_ai(db, current_user):
            record_ask_ai_block(db, current_user.id)
            db.commit()
            return blocked_response_payload(db, current_user)

    mode = payload.mode
    research_docs: list[dict] = []
    private_rows: list[UserPrivateDocument] = []

    if mode in ("research_only", "research_and_documents"):
        retrieval = RetrievalService(db)
        research_docs = retrieval.retrieve_for_condition(
            condition_id=condition.id,
            query=payload.prompt,
            limit=5,
            age_scope=follow.age_scope,
            geography=follow.geography,
        )

    if mode in ("documents_only", "research_and_documents"):
        private_rows = _load_private_documents(
            db,
            user_id=current_user.id,
            condition_id=condition.id,
            document_ids=payload.document_ids,
        )

    if mode == "research_only":
        if not research_docs:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_research_unavailable_detail(db, condition.id))
    elif mode == "documents_only":
        if not private_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No processed documents found for this condition. Upload a PDF on the Ask AI tab and wait for processing, or adjust your document filter.",
            )
    else:
        if not research_docs and not private_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Neither indexed research nor your uploaded documents are available for this question. "
                + _research_unavailable_detail(db, condition.id),
            )

    research_chunks: list[str] = []
    for d in research_docs:
        research_chunks.append(
            "\n".join(
                [
                    f"ID: {d['research_item_id']}",
                    f"Title: {d['title']}",
                    f"Type: {d['item_type']}",
                    f"Published: {d.get('published_at') or ''}",
                    f"URL: {d['source_url']}",
                    f"Body: {(d.get('abstract_or_body') or '')[:2200]}",
                ]
            )
        )
    research_text = "\n\n---\n\n".join(research_chunks)

    private_text, allowed_private = build_private_context_chunks(private_rows)
    if mode == "documents_only" and not private_text.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No usable extracted text in your documents yet. Wait for processing to finish, or upload a text-based PDF.",
        )

    answer_lang = payload.answer_locale or ("he" if current_user.preferred_locale == "he" else "en")

    intent = infer_intent_heuristic(payload.prompt)
    used_aggregated_evidence = False
    aggregation_documents: list[NormalizedMedicalDocument] | None = None
    if (
        settings.medical_intel_aggregated_evidence_in_ask_ai
        and research_docs
        and mode in ("research_only", "research_and_documents")
    ):
        try:
            legacy_norm = build_legacy_normalized_documents(
                db,
                research_docs,
                condition_name=condition.canonical_name,
                answer_lang=answer_lang,
            )
            live_norm = asyncio.run(
                fetch_live_normalized_documents(
                    query=payload.prompt,
                    condition_name=condition.canonical_name,
                    intent=intent,
                    limit_per_provider=4,
                    db=db,
                )
            )
            agg = aggregate_and_rank(
                legacy_norm,
                live_norm,
                user_query=payload.prompt,
                intent=intent,
                condition_name=condition.canonical_name,
            )
            # Never drop indexed hits from the prompt: only switch layout if every retrieval row bridged to ORM.
            if len(legacy_norm) < len(research_docs):
                _ask_ai_log.warning(
                    "ask_ai aggregation skipped: legacy bridge %s/%s rows; keeping classic TRUSTED_INDEXED_EVIDENCE",
                    len(legacy_norm),
                    len(research_docs),
                )
            elif agg.documents:
                research_text = format_aggregated_evidence_for_prompt(agg.documents)
                used_aggregated_evidence = True
                aggregation_documents = agg.documents
                _ask_ai_log.info(
                    "ask_ai using aggregated evidence legacy=%s live=%s dedup_removed=%s top_sources=%s",
                    agg.legacy_count,
                    agg.live_count,
                    agg.duplicates_removed,
                    agg.top_source_names,
                )
            else:
                _ask_ai_log.info(
                    "ask_ai aggregation returned no documents; keeping classic TRUSTED_INDEXED_EVIDENCE (%s retrieval rows)",
                    len(research_docs),
                )
        except Exception:  # noqa: BLE001
            _ask_ai_log.exception(
                "ask_ai aggregated evidence failed; classic retrieval layout. research_docs=%s",
                len(research_docs),
            )

    lang_rule = (
        "Write every user-facing string in the JSON response in Hebrew (modern, plain language suitable for patients and families). "
        "Keep source titles in the evidence list close to the original English if that is how they appear in the index."
        if answer_lang == "he"
        else "Write every user-facing string in the JSON response in clear English suitable for patients and families."
    )

    _focus_rules = {
        "pediatric": "This user is focused on pediatric (child/adolescent) context — prioritize evidence that applies to children and teens, not adult-only studies, unless the question clearly requires broader context.",
        "adult": "This user is focused on adult context — prioritize evidence that applies to adults; deprioritize pediatric-only work unless it is essential to the question.",
        "both": "This user asked for both pediatric and adult relevance where applicable — balance evidence across ages when the question is broad.",
    }
    _ak = (follow.age_scope or "both").strip().lower()
    audience_text = _focus_rules.get(_ak, _focus_rules["both"])
    geo = (follow.geography or "").strip()
    geo_note = (
        f" Geographic interest: {geo}. When trials or sites list countries, slightly prefer evidence with activity in that region when choosing what to emphasize."
        if geo and geo.lower() not in ("global", "worldwide", "")
        else ""
    )
    audience_rule = f"{audience_text}{geo_note}"

    if mode == "research_only":
        if used_aggregated_evidence:
            scope_rule = (
                "Answer only about the selected condition using the AGGREGATED_RANKED_EVIDENCE block below. "
                "It combines trusted indexed items (PubMed, ClinicalTrials.gov, openFDA) with reference library "
                "snippets (Orphadata/Orphanet, MedlinePlus) when available. "
                "Use simple language. Include uncertainty when evidence is weak. "
                "Do not provide diagnosis, dosing, emergency or treatment-change advice. "
                "In sources[], set research_item_id only for lines that include a real research_item_id; "
                "for reference-only rows without an id, cite the URL in prose and omit research_item_id in sources[]."
            )
            user_blocks = ["AGGREGATED_RANKED_EVIDENCE:\n" + research_text]
        else:
            scope_rule = (
                "Answer only about the selected condition and only from the TRUSTED_INDEXED_EVIDENCE block below. "
                "Use simple language. Include uncertainty when evidence is weak. "
                "Do not provide diagnosis, dosing, emergency or treatment-change advice. "
                "In sources[], set research_item_id from the evidence IDs; leave document_id empty."
            )
            user_blocks = ["TRUSTED_INDEXED_EVIDENCE:\n" + research_text]
    elif mode == "documents_only":
        scope_rule = (
            "Answer only about the selected condition and only from the USER_UPLOADED_DOCUMENTS block below. "
            "These are the user's own files—not peer-reviewed research feeds. Do not invent facts not supported by that text. "
            "Do not provide diagnosis, dosing, emergency or treatment-change advice. "
            "In sources[], set document_id from DOCUMENT_ID lines; leave research_item_id empty; source_url may be empty."
        )
        user_blocks = ["USER_UPLOADED_DOCUMENTS:\n" + private_text]
    else:
        if used_aggregated_evidence:
            scope_rule = (
                "You may use AGGREGATED_RANKED_EVIDENCE (indexed + reference libraries) and USER_UPLOADED_DOCUMENTS "
                "(the user's own PDF text). Never attribute private document text to the research index or vice versa. "
                "Do not provide diagnosis, dosing, emergency or treatment-change advice. "
                "In sources[], cite research_item_id for indexed items when present; use document_id for uploads; "
                "for reference-only rows without research_item_id, cite URL in prose and omit research_item_id in sources[]."
            )
        else:
            scope_rule = (
                "You may use two separate blocks: TRUSTED_INDEXED_EVIDENCE (curated research index) and USER_UPLOADED_DOCUMENTS "
                "(the user's own PDF text). Never attribute private document text to the research index or vice versa. "
                "Do not provide diagnosis, dosing, emergency or treatment-change advice. "
                "In sources[], cite research_item_id for index items and document_id for uploads (one or the other per row)."
            )
        parts = []
        if research_text:
            label = "AGGREGATED_RANKED_EVIDENCE" if used_aggregated_evidence else "TRUSTED_INDEXED_EVIDENCE"
            parts.append(f"{label}:\n" + research_text)
        if private_text:
            parts.append("USER_UPLOADED_DOCUMENTS:\n" + private_text)
        user_blocks = parts

    safety_hints = medical_attention_hints(payload.prompt, locale=answer_lang)
    safety_extra = ""
    if safety_hints:
        safety_extra = " Additional safety guidance for this question: " + " ".join(safety_hints) + (
            " Reinforce that you are not a substitute for a clinician; suggest timely medical contact when appropriate."
        )

    system_base = f"You are CureCompass Ask AI. {scope_rule} {audience_rule} {lang_rule}{safety_extra}"

    structured_extra = ""
    if settings.medical_intel_structured_answer:
        grounding_primary = (
            "Use only the labeled evidence blocks as the source of medical facts. "
            "When AGGREGATED_RANKED_EVIDENCE is present, treat it as the primary ranked grounding set for clinical claims. "
        )
        if used_aggregated_evidence:
            grounding_primary = (
                "AGGREGATED_RANKED_EVIDENCE (below) is the primary ranked grounding set—prefer it over any optional hints. "
            )
        structured_extra = (
            " STRUCTURED_JSON_EXTENSIONS: Fill every key in the JSON schema including simple_explanation "
            "(plain language for someone without medical training—briefly explain terms like benign, mutation, "
            "or clinical trial phase when you use them) plus key_facts, approved_treatments, "
            "experimental_or_emerging_options, relevant_clinical_trials, warning_signs_or_when_to_seek_care, "
            "what_is_uncertain. "
            + grounding_primary
            + "Do not diagnose. Do not invent treatments, trial IDs, drugs, doses, or certainty beyond the supplied text. "
            "Clearly separate regulatory-approved options explicitly supported by trustworthy sources in the evidence "
            "from experimental or early-stage work; if unclear, say so in what_is_uncertain. "
            "When a section is unsupported, use a short phrase such as 'Not covered in the supplied evidence.' "
            "Keep legacy fields accurate and grounded: direct_answer, what_changed_recently, evidence_strength, "
            "available_now_or_experimental, suggested_doctor_questions, sources. "
            + intent_structured_guidance(intent)
        )

    use_structured = settings.medical_intel_structured_answer
    system = system_base + structured_extra if use_structured else system_base

    live_reference_tail = ""
    if (
        not used_aggregated_evidence
        and settings.medical_intel_live_in_ask_ai
        and research_docs
        and mode in ("research_only", "research_and_documents")
    ):
        try:
            hint_block = fetch_live_reference_block_sync(
                query=payload.prompt,
                condition_name=condition.canonical_name,
                intent=intent,
                limit_per_provider=4,
                db=db,
            )
            if hint_block.strip():
                live_reference_tail = (
                    "\n\nLIVE_REFERENCE_HINTS (Orphadata / MedlinePlus reference text; cite URLs in prose if helpful; "
                    "do not fabricate research_item_id for these):\n"
                    + hint_block
                )
        except Exception:  # noqa: BLE001 — optional enrichment; never fail Ask AI
            live_reference_tail = ""

    id_instruction = (
        "\n\nUse research_item_id from the evidence blocks in sources[] only when a line includes a real "
        "research_item_id; omit it for reference-only rows and cite the URL in prose instead."
        if used_aggregated_evidence
        else "\n\nUse only the IDs provided in the evidence blocks in the sources list."
    )
    user = (
        f"Condition: {condition.canonical_name}\n"
        f"Follow preferences — age scope: {follow.age_scope}; region note: {geo or 'global'}.\n"
        f"User question: {payload.prompt}\n\n"
        + "\n\n".join(user_blocks)
        + id_instruction
        + live_reference_tail
    )

    client = OpenAI(api_key=settings.openai_api_key)

    answer_payload: dict
    parsed_core: AskAIAnswerOut

    if use_structured:
        try:
            raw = _openai_ask_ai_raw(client, system=system, user=user, schema_model=AskAIStructuredLLMSchema)
            parsed_st = AskAIStructuredLLMSchema.model_validate(json.loads(raw))
            trusted = build_trusted_sources_from_ranked_evidence(
                aggregated_ranked_documents=aggregation_documents,
                research_docs=research_docs,
                used_aggregated_evidence=used_aggregated_evidence,
                private_documents=[(str(p.id), p.original_filename) for p in private_rows],
                mode=mode,
            )
            answer_payload = merge_structured_into_answer_payload(parsed_st, trusted_sources=trusted)
            parsed_core = AskAIAnswerOut.model_validate(answer_payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            _ask_ai_log.warning("Ask AI structured output failed; falling back to classic schema: %s", exc)
            raw = _openai_ask_ai_raw(client, system=system_base, user=user, schema_model=AskAIAnswerOut)
            parsed_core = AskAIAnswerOut.model_validate(json.loads(raw))
            answer_payload = parsed_core.model_dump()
    else:
        raw = _openai_ask_ai_raw(client, system=system_base, user=user, schema_model=AskAIAnswerOut)
        parsed_core = AskAIAnswerOut.model_validate(json.loads(raw))
        answer_payload = parsed_core.model_dump()

    allowed_by_id = {d["research_item_id"]: d for d in research_docs}
    validated_sources: list[dict] = []
    for s in parsed_core.sources:
        did = (s.document_id or "").strip()
        rid = (s.research_item_id or "").strip()
        if did and did in allowed_private:
            doc = allowed_private[did]
            validated_sources.append(
                {
                    "research_item_id": "",
                    "document_id": did,
                    "title": doc.original_filename,
                    "source_url": "",
                    "published_at": "",
                    "item_type": "user_document",
                }
            )
        elif rid and rid in allowed_by_id:
            canonical = allowed_by_id[rid]
            validated_sources.append(
                {
                    "research_item_id": rid,
                    "document_id": "",
                    "title": canonical["title"],
                    "source_url": canonical["source_url"],
                    "published_at": canonical.get("published_at") or "",
                    "item_type": canonical["item_type"],
                }
            )

    if not validated_sources:
        for d in research_docs[:3]:
            validated_sources.append(
                {
                    "research_item_id": d["research_item_id"],
                    "document_id": "",
                    "title": d["title"],
                    "source_url": d["source_url"],
                    "published_at": d.get("published_at") or "",
                    "item_type": d["item_type"],
                }
            )
        for doc in list(allowed_private.values())[:3]:
            if len(validated_sources) >= 5:
                break
            validated_sources.append(
                {
                    "research_item_id": "",
                    "document_id": str(doc.id),
                    "title": doc.original_filename,
                    "source_url": "",
                    "published_at": "",
                    "item_type": "user_document",
                }
            )

    conversation = None
    if payload.conversation_id:
        try:
            conversation = db.get(AskAIConversation, UUID(payload.conversation_id))
        except ValueError:
            conversation = None
        if not conversation or conversation.user_id != current_user.id or conversation.condition_id != condition.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        conversation = AskAIConversation(user_id=current_user.id, condition_id=condition.id)
        db.add(conversation)
        db.flush()

    db.add(
        AskAIMessage(
            conversation_id=conversation.id,
            role="user",
            content=payload.prompt,
            structured_json={"mode": mode, "document_ids": payload.document_ids},
            citations_json=[],
        )
    )
    answer_payload["sources"] = validated_sources
    db.add(
        AskAIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=parsed_core.direct_answer,
            structured_json=answer_payload,
            citations_json=validated_sources,
        )
    )
    if should_enforce_ask_ai_limit(current_user):
        increment_successful_ask(db, current_user.id)
    db.commit()

    return {
        "conversation_id": str(conversation.id),
        **answer_payload,
        **success_usage_extras(db, current_user),
    }


@router.get("/ask-ai/daily-usage")
def get_ask_ai_daily_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Today's free-tier Ask AI usage (UTC). Premium users see unlimited remaining."""
    snap = user_ask_ai_usage_snapshot(db, current_user)
    out: dict = {"usage": snap}
    if snap.get("is_limited") and not snap.get("is_premium"):
        out["limit_message"] = FREE_DAILY_LIMIT_MESSAGE
    return out


@router.get("/conditions/{slug}/ask-ai/conversations")
def list_conversations(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    rows = db.scalars(
        select(AskAIConversation)
        .where(AskAIConversation.user_id == current_user.id, AskAIConversation.condition_id == condition.id)
        .order_by(AskAIConversation.created_at.desc())
        .limit(50)
    ).all()
    return [{"id": str(r.id), "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/ask-ai/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_id = UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid conversation id") from exc

    conversation = db.get(AskAIConversation, parsed_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = db.scalars(
        select(AskAIMessage)
        .where(AskAIMessage.conversation_id == conversation.id)
        .order_by(AskAIMessage.created_at.asc())
    ).all()
    return {
        "id": str(conversation.id),
        "condition_id": str(conversation.condition_id),
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "structured_json": m.structured_json,
                "citations_json": m.citations_json,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }
