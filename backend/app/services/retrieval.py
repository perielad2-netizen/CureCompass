import math
import uuid
from typing import Any

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import ResearchItem, ResearchItemAI, ResearchItemEmbedding, Source, Trial
from app.services.follow_relevance import (
    combined_personalization_multiplier,
    countries_for_item,
    infer_item_audience,
    normalize_user_age_scope,
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class RetrievalService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.openai_api_key)

    def retrieve_for_condition(
        self,
        *,
        condition_id: str | uuid.UUID,
        query: str,
        limit: int = 5,
        age_scope: str | None = None,
        geography: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over research_items for one condition.

        Only items whose ``Source`` is ``enabled`` and ``trust_score >= 0.8`` are considered (seeded PubMed /
        ClinicalTrials.gov / openFDA are ~0.95–0.97). Items without embeddings still rank by trust + recency constant term.

        When ``age_scope`` is ``pediatric`` or ``adult``, cohort mismatches are strongly downranked; geography
        gives a modest boost when trial countries align with the user's region.
        """
        cid = uuid.UUID(str(condition_id)) if not isinstance(condition_id, uuid.UUID) else condition_id
        scope = normalize_user_age_scope(age_scope)
        emb_resp = self.client.embeddings.create(model=settings.openai_embedding_model, input=query, timeout=30)
        q_embedding = emb_resp.data[0].embedding

        recent_cap = 220 if scope != "both" else 120
        rows = self.db.execute(
            select(ResearchItem, Source, ResearchItemEmbedding, ResearchItemAI)
            .join(Source, Source.id == ResearchItem.source_id)
            .join(ResearchItemEmbedding, ResearchItemEmbedding.research_item_id == ResearchItem.id, isouter=True)
            .join(ResearchItemAI, ResearchItemAI.research_item_id == ResearchItem.id, isouter=True)
            .where(
                ResearchItem.condition_id == cid,
                Source.enabled.is_(True),
                Source.trust_score >= 0.8,
            )
            .order_by(ResearchItem.published_at.desc())
            .limit(recent_cap)
        ).all()

        rids = [row[0].id for row in rows]
        trial_by_item: dict[uuid.UUID, Trial] = {}
        if rids:
            tr_rows = self.db.scalars(select(Trial).where(Trial.research_item_id.in_(rids))).all()
            for tr in tr_rows:
                if tr.research_item_id:
                    trial_by_item[tr.research_item_id] = tr

        scored: list[tuple[float, ResearchItem, Source]] = []
        for item, source, emb, ai in rows:
            sim = 0.0
            if emb and emb.embedding:
                sim = _cosine_similarity(q_embedding, emb.embedding)
            # recency + trust + semantic
            base = (sim * 0.7) + (float(source.trust_score) * 0.2) + 0.1
            trial = trial_by_item.get(item.id)
            aud = infer_item_audience(item, ai, trial)
            countries = countries_for_item(item, trial)
            mult = combined_personalization_multiplier(
                user_age_scope=age_scope,
                user_geography=geography,
                item_audience=aud,
                countries=countries,
            )
            score = base * mult
            scored.append((score, item, source))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]
        return [
            {
                "research_item_id": str(item.id),
                "title": item.title,
                "source_url": item.source_url,
                "source_name": source.name,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "item_type": item.item_type,
                "abstract_or_body": item.abstract_or_body,
                "retrieval_rank": rank,
                "retrieval_score": float(score),
            }
            for rank, (score, item, source) in enumerate(top)
        ]
