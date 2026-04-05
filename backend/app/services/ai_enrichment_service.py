import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Condition, EvidenceStage, ResearchItem, ResearchItemAI, ResearchItemEmbedding
from app.core.config import settings
from app.schemas.ai_enrichment import ResearchItemEnrichmentOut
from app.services.openai_json_schema import patch_json_schema_for_openai_strict


@dataclass
class EnrichmentStats:
    enriched: int
    skipped: int
    failed: int


class AIEnrichmentService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=settings.openai_api_key)

    def _build_input(self, condition: Condition, item: ResearchItem) -> str:
        # Keep the model grounded in indexed source content and avoid any “medical advice” framing.
        return "\n\n".join(
            [
                f"Condition: {condition.canonical_name}",
                f"Source type: {item.item_type}",
                f"Source URL: {item.source_url}",
                f"Published: {item.published_at.isoformat() if item.published_at else ''}",
                f"Title: {item.title}",
                f"Abstract/body: {item.abstract_or_body[:8000] if item.abstract_or_body else ''}",
            ]
        )

    def _json_schema_text_config(self) -> dict[str, Any]:
        schema = ResearchItemEnrichmentOut.model_json_schema()
        patch_json_schema_for_openai_strict(schema)
        return {
            "format": {
                "type": "json_schema",
                "name": "ResearchItemEnrichmentOut",
                "schema": schema,
                "strict": True,
            }
        }

    def enrich_one(self, condition: Condition, item: ResearchItem) -> ResearchItemEnrichmentOut:
        system = (
            "You are a careful medical research explainer for patients and caregivers. "
            "You must only summarize research and trusted updates from the provided indexed source text. "
            "Do NOT give personal medical advice. Do NOT recommend starting, stopping, or changing treatment. "
            "Use simple language. Clearly label evidence strength and whether it is available now or still experimental. "
            "Use the provided taxonomy and output ONLY valid JSON matching the schema. "
            "Always include lay_summary_he and why_it_matters_he: the same factual meaning as lay_summary and "
            "why_it_matters, written in clear modern Hebrew for Israeli patients and families (not literal "
            "word-for-word translation if that harms clarity). Keep Hebrew concise and neutral."
        )

        prompt_input = self._build_input(condition, item)

        resp = self.client.responses.create(
            model=settings.openai_responses_model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_input},
            ],
            text=self._json_schema_text_config(),
            timeout=90,
        )

        # responses API returns JSON in output_text when using json_schema response_format.
        raw = getattr(resp, "output_text", None)
        if not raw:
            # fallback: try to find text in structured output array
            try:
                out0 = resp.output[0]  # type: ignore[index]
                content0 = out0.content[0]  # type: ignore[index]
                raw = getattr(content0, "text", None) or getattr(content0, "output_text", None)
            except Exception:  # noqa: BLE001
                raw = None

        if not raw:
            raise ValueError("No JSON output received from OpenAI responses")

        data = json.loads(raw)
        return ResearchItemEnrichmentOut.model_validate(data)

    def _upsert_ai_row(self, item: ResearchItem, out: ResearchItemEnrichmentOut) -> None:
        row = self.db.scalar(select(ResearchItemAI).where(ResearchItemAI.research_item_id == item.id))
        payload = out.model_dump()

        evidence_enum = EvidenceStage(out.evidence_stage.value)

        if row is None:
            self.db.add(
                ResearchItemAI(
                    research_item_id=item.id,
                    lay_summary=out.lay_summary,
                    lay_summary_he=out.lay_summary_he,
                    clinician_summary=out.clinician_summary,
                    why_it_matters=out.why_it_matters,
                    why_it_matters_he=out.why_it_matters_he,
                    evidence_stage=evidence_enum,
                    confidence_level=out.confidence_level,
                    hype_risk=out.hype_risk.value,
                    applicability_age_group=out.applicability_age_group,
                    relevance_score=out.relevance_score,
                    novelty_score=out.novelty_score,
                    actionability_score=out.actionability_score,
                    structured_json=payload,
                    model_name=settings.openai_responses_model,
                    prompt_version="v1_phase4_enrichment_bilingual",
                )
            )
            return

        row.lay_summary = out.lay_summary
        row.lay_summary_he = out.lay_summary_he
        row.clinician_summary = out.clinician_summary
        row.why_it_matters = out.why_it_matters
        row.why_it_matters_he = out.why_it_matters_he
        row.evidence_stage = evidence_enum
        row.confidence_level = out.confidence_level
        row.hype_risk = out.hype_risk.value
        row.applicability_age_group = out.applicability_age_group
        row.relevance_score = out.relevance_score
        row.novelty_score = out.novelty_score
        row.actionability_score = out.actionability_score
        row.structured_json = payload
        row.model_name = settings.openai_responses_model
        row.prompt_version = "v1_phase4_enrichment_bilingual"

    def _embed_text(self, text: str) -> list[float]:
        # Embeddings use the embeddings API (not Responses API). This keeps Phase 4 integration practical.
        resp = self.client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
            timeout=30,
        )
        return resp.data[0].embedding  # type: ignore[no-any-return]

    def _upsert_embedding(self, item: ResearchItem, embedding: list[float]) -> None:
        row = self.db.scalar(
            select(ResearchItemEmbedding).where(ResearchItemEmbedding.research_item_id == item.id)
        )
        if row is None:
            self.db.add(ResearchItemEmbedding(research_item_id=item.id, embedding=embedding))
        else:
            row.embedding = embedding

    def enrich_condition(self, condition: Condition, *, limit: int | None = None) -> EnrichmentStats:
        q = (
            select(ResearchItem)
            .where(ResearchItem.condition_id == condition.id)
            .order_by(ResearchItem.published_at.desc())
        )
        items = self.db.scalars(q).all()
        if limit is not None:
            items = items[:limit]

        stats = EnrichmentStats(enriched=0, skipped=0, failed=0)
        for item in items:
            existing = self.db.scalar(select(ResearchItemAI).where(ResearchItemAI.research_item_id == item.id))
            if existing and (existing.lay_summary_he or "").strip():
                stats.skipped += 1
                continue

            try:
                out = self.enrich_one(condition, item)
                self._upsert_ai_row(item, out)

                embed_text = f"{item.title}\n\n{item.abstract_or_body[:8000] if item.abstract_or_body else ''}"
                embedding = self._embed_text(embed_text)
                self._upsert_embedding(item, embedding)

                self.db.commit()
                stats.enriched += 1
            except Exception:  # noqa: BLE001
                self.db.rollback()
                stats.failed += 1

        return stats

