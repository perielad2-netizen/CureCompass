import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import AskAIConversation, AskAIMessage, Condition, ResearchItem, Source, User, UserFollowedCondition
from app.schemas.ask_ai import AskAIAnswerOut, AskAIIn
from app.services.ask_ai_guard import enforce_condition_scope
from app.services.openai_json_schema import patch_json_schema_for_openai_strict
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

    retrieval = RetrievalService(db)
    docs = retrieval.retrieve_for_condition(condition_id=condition.id, query=payload.prompt, limit=5)
    if not docs:
        n_any = db.scalar(select(func.count()).select_from(ResearchItem).where(ResearchItem.condition_id == condition.id))
        n_trusted = db.scalar(
            select(func.count())
            .select_from(ResearchItem)
            .join(Source, Source.id == ResearchItem.source_id)
            .where(ResearchItem.condition_id == condition.id, Source.trust_score >= 0.8)
        )
        if (n_any or 0) == 0:
            detail = (
                "There are no indexed research items for this condition yet, so Ask AI has nothing to search. "
                "Use “Check for updates” on your dashboard (or run ingestion) to pull records from PubMed, "
                "ClinicalTrials.gov, and openFDA. Ask AI only answers from those trusted indexed sources."
            )
        else:
            detail = (
                f"This condition has {n_any} indexed item(s), but none are attached to a source with trust score ≥ 0.8, "
                "which Ask AI requires. Re-seed sources (PubMed, ClinicalTrials.gov, openFDA) or fix Source.trust_score in the database."
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    context_chunks = []
    for d in docs:
        context_chunks.append(
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
    context_text = "\n\n---\n\n".join(context_chunks)

    system = (
        "You are CureCompass Ask AI. "
        "Answer only about the selected condition and only from provided trusted indexed evidence. "
        "Use simple language. Include uncertainty when evidence is weak. "
        "Do not provide diagnosis, dosing, emergency or treatment-change advice."
    )
    user = (
        f"Condition: {condition.canonical_name}\n"
        f"User question: {payload.prompt}\n\n"
        "Evidence:\n"
        f"{context_text}\n\n"
        "Use provided evidence IDs in the sources list."
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

    # Enforce citations from retrieved docs only.
    allowed_by_id = {d["research_item_id"]: d for d in docs}
    validated_sources = []
    for s in parsed.sources:
        sid = s.research_item_id
        if sid in allowed_by_id:
            canonical = allowed_by_id[sid]
            validated_sources.append(
                {
                    "research_item_id": sid,
                    "title": canonical["title"],
                    "source_url": canonical["source_url"],
                    "published_at": canonical.get("published_at") or "",
                    "item_type": canonical["item_type"],
                }
            )
    if not validated_sources:
        validated_sources = [
            {
                "research_item_id": d["research_item_id"],
                "title": d["title"],
                "source_url": d["source_url"],
                "published_at": d.get("published_at") or "",
                "item_type": d["item_type"],
            }
            for d in docs[:3]
        ]

    # Conversation state
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
            structured_json={},
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

