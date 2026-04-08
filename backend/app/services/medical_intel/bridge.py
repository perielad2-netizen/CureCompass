"""Map existing ORM rows into ``NormalizedMedicalDocument`` for one aggregation pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.entities import ResearchItem, Source
from app.schemas.medical_intel import MedicalEntityType, NormalizedMedicalDocument
from app.services.medical_intel.trust import default_reliability_for_source_name


def _entity_type_for_item_type(item_type: str) -> MedicalEntityType:
    t = (item_type or "").strip().lower()
    if t == "trial":
        return "clinical_trial"
    if t == "paper":
        return "research_paper"
    if t == "regulatory":
        return "safety_warning"
    return "other"


def _freshness(published_at: datetime | None) -> float:
    if published_at is None:
        return 0.4
    now = datetime.now(tz=timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    days = (now - published_at).total_seconds() / 86400.0
    # Soft decay: last 30d ~1.0, 365d ~0.5, older lower
    if days <= 0:
        return 1.0
    if days >= 730:
        return 0.2
    return max(0.15, 1.0 - (days / 730.0) * 0.8)


def research_item_to_normalized(
    item: ResearchItem,
    source: Source,
    *,
    plain_language_summary: str = "",
    condition_name: str = "",
    relevance_score: float = 0.5,
) -> NormalizedMedicalDocument:
    """Bridge ``ResearchItem`` + ``Source`` to unified schema (scores are defaults unless set by ranker)."""
    src_name = source.name or ""
    et = _entity_type_for_item_type(item.item_type)
    rid = str(item.id)
    return NormalizedMedicalDocument(
        id=f"research_item:{rid}",
        entity_type=et,
        title=item.title or "",
        source_name=src_name,
        source_url=item.source_url or "",
        summary=(item.abstract_or_body or "")[:4000],
        plain_language_summary=plain_language_summary,
        condition_name=condition_name,
        keywords=[],
        reliability_score=float(source.trust_score or default_reliability_for_source_name(src_name)),
        relevance_score=relevance_score,
        freshness_score=_freshness(item.published_at),
        published_at=item.published_at,
        raw_data={
            "external_id": item.external_id,
            "item_type": item.item_type,
            "source_id": str(source.id),
        },
        internal_research_item_id=rid,
    )
