import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI
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
from app.schemas.ask_ai import AskAIAnswerOut, AskAIIn
from app.services.ask_ai_guard import enforce_condition_scope
from app.services.openai_json_schema import patch_json_schema_for_openai_strict
from app.services.private_document_pipeline import build_private_context_chunks
from app.services.retrieval import RetrievalService

router = APIRouter(tags=["ask-ai"])


def _ask_ai_schema_text_config() -> dict:
    schema = AskAIAnswerOut.model_json_schema()
    patch_json_schema_for_openai_strict(schema)

    return {
        "format": {
            "type": "json_schema",
            "name": "AskAIAnswerOut",
            "schema": schema,
            "strict": True,
        }
    }


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

    mode = payload.mode
    research_docs: list[dict] = []
    private_rows: list[UserPrivateDocument] = []

    if mode in ("research_only", "research_and_documents"):
        retrieval = RetrievalService(db)
        research_docs = retrieval.retrieve_for_condition(condition_id=condition.id, query=payload.prompt, limit=5)

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
    lang_rule = (
        "Write every user-facing string in the JSON response in Hebrew (modern, plain language suitable for patients and families). "
        "Keep source titles in the evidence list close to the original English if that is how they appear in the index."
        if answer_lang == "he"
        else "Write every user-facing string in the JSON response in clear English suitable for patients and families."
    )

    if mode == "research_only":
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
        scope_rule = (
            "You may use two separate blocks: TRUSTED_INDEXED_EVIDENCE (curated research index) and USER_UPLOADED_DOCUMENTS "
            "(the user's own PDF text). Never attribute private document text to the research index or vice versa. "
            "Do not provide diagnosis, dosing, emergency or treatment-change advice. "
            "In sources[], cite research_item_id for index items and document_id for uploads (one or the other per row)."
        )
        parts = []
        if research_text:
            parts.append("TRUSTED_INDEXED_EVIDENCE:\n" + research_text)
        if private_text:
            parts.append("USER_UPLOADED_DOCUMENTS:\n" + private_text)
        user_blocks = parts

    system = f"You are CureCompass Ask AI. {scope_rule} {lang_rule}"
    user = (
        f"Condition: {condition.canonical_name}\n"
        f"User question: {payload.prompt}\n\n"
        + "\n\n".join(user_blocks)
        + "\n\nUse only the IDs provided in the evidence blocks in the sources list."
    )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_responses_model,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        text=_ask_ai_schema_text_config(),
        timeout=90,
    )
    raw = getattr(response, "output_text", None)
    if not raw:
        try:
            raw = response.output[0].content[0].text  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Ask AI output parsing failed: {exc}") from exc

    parsed = AskAIAnswerOut.model_validate(json.loads(raw))

    allowed_by_id = {d["research_item_id"]: d for d in research_docs}
    validated_sources: list[dict] = []
    for s in parsed.sources:
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
    answer_payload = parsed.model_dump()
    answer_payload["sources"] = validated_sources
    db.add(
        AskAIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=parsed.direct_answer,
            structured_json=answer_payload,
            citations_json=validated_sources,
        )
    )
    db.commit()

    return {"conversation_id": str(conversation.id), **answer_payload}


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
