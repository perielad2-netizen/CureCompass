import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Condition, ResearchItem, Source, Trial
from app.services.adapters.base import SourceAdapter


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_date_or_now(value: Any) -> datetime:
    if isinstance(value, str):
        # Handles ISO dates like "2020-01-31"
        try:
            if len(value) == 10:
                return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return _utc_now()


@dataclass
class IngestionResult:
    condition_slug: str
    ingested_items: int
    updated_items: int


class IngestionService:
    def __init__(self, db: Session, adapters: list[SourceAdapter]):
        self.db = db
        self.adapters = adapters

    async def ingest_for_condition(self, condition: Condition) -> IngestionResult:
        ingested = 0
        updated = 0

        for adapter in self.adapters:
            # Lookup the configured source row by adapter identity.
            source_row = self.db.scalar(select(Source).where(Source.name == adapter.name, Source.enabled.is_(True)))
            if not source_row:
                continue

            # Adapters fetch using condition canonical name for better coverage.
            try:
                raw_items = await adapter.fetch_updates(condition.canonical_name)
            except Exception:
                # Adapter failures should not break the whole backfill run.
                # Each adapter has its own downstream trust/rate limitations.
                raw_items = []
            for raw in raw_items:
                normalized = adapter.normalize(raw)
                external_id = str(normalized["external_id"])
                item_type = str(normalized.get("item_type", "paper"))
                published_at = _parse_date_or_now(normalized.get("published_at"))

                existing = self.db.scalar(
                    select(ResearchItem).where(
                        ResearchItem.condition_id == condition.id,
                        ResearchItem.source_id == source_row.id,
                        ResearchItem.external_id == external_id,
                        ResearchItem.item_type == item_type,
                    )
                )

                if existing:
                    existing.title = normalized["title"]
                    existing.abstract_or_body = normalized.get("abstract_or_body", "") or ""
                    existing.source_url = normalized["source_url"]
                    existing.published_at = published_at
                    existing.raw_json = raw
                    existing.normalized_metadata_json = normalized.get("normalized_metadata", normalized)
                    updated += 1
                else:
                    item = ResearchItem(
                        condition_id=condition.id,
                        source_id=source_row.id,
                        external_id=external_id,
                        item_type=item_type,
                        title=normalized["title"],
                        abstract_or_body=normalized.get("abstract_or_body", "") or "",
                        source_url=normalized["source_url"],
                        published_at=published_at,
                        raw_json=raw,
                        normalized_metadata_json=normalized.get("normalized_metadata", normalized),
                    )
                    self.db.add(item)
                    self.db.flush()  # obtain id without full commit
                    ingested += 1

                    # If the adapter also provides trial details, create Trials rows.
                    if normalized.get("trial"):
                        t = normalized["trial"]
                        self._upsert_trial(condition.id, item.id, source_row.id, external_id, t)

            self.db.commit()

            # Gentle throttle to be nicer to downstream sources.
            await asyncio.sleep(0.25)

        self.db.commit()
        return IngestionResult(condition_slug=condition.slug, ingested_items=ingested, updated_items=updated)

    def _upsert_trial(
        self,
        condition_id: Any,
        research_item_id: Any,
        _source_id: Any,
        nct_id: str,
        t: dict,
    ) -> None:
        existing = self.db.scalar(select(Trial).where(Trial.nct_id == nct_id))
        if existing:
            existing.research_item_id = research_item_id
            existing.status = t.get("status", "") or ""
            existing.phase = t.get("phase", "") or ""
            existing.title = t.get("title", "") or ""
            existing.intervention = t.get("intervention", "") or ""
            existing.eligibility_summary = t.get("eligibility_summary", "") or ""
            existing.age_min = t.get("age_min")
            existing.age_max = t.get("age_max")
            existing.sex = t.get("sex", "all") or "all"
            existing.countries_json = t.get("countries_json", []) or []
            existing.locations_json = t.get("locations_json", []) or []
            existing.primary_endpoint = t.get("primary_endpoint", "") or ""
            existing.primary_endpoint_plain_language = t.get("primary_endpoint_plain_language", "") or ""
            existing.last_verified_at = _utc_now()
            return

        self.db.add(
            Trial(
                condition_id=condition_id,
                research_item_id=research_item_id,
                nct_id=nct_id,
                status=t.get("status", "") or "",
                phase=t.get("phase", "") or "",
                title=t.get("title", "") or "",
                intervention=t.get("intervention", "") or "",
                eligibility_summary=t.get("eligibility_summary", "") or "",
                age_min=t.get("age_min"),
                age_max=t.get("age_max"),
                sex=t.get("sex", "all") or "all",
                countries_json=t.get("countries_json", []) or [],
                locations_json=t.get("locations_json", []) or [],
                primary_endpoint=t.get("primary_endpoint", "") or "",
                primary_endpoint_plain_language=t.get("primary_endpoint_plain_language", "") or "",
                last_verified_at=_utc_now(),
            )
        )

