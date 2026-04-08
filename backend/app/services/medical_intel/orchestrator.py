"""Query multiple MedicalIntel providers, normalize, dedupe, format for LLM context."""

from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.schemas.medical_intel import NormalizedMedicalDocument
from app.services.medical_intel.intent import UserIntent
from app.services.medical_intel.provider import MedicalIntelProvider
from app.services.medical_intel.registry import filter_live_providers_by_source_enabled, providers_for_intent


def _dedupe(docs: list[NormalizedMedicalDocument]) -> list[NormalizedMedicalDocument]:
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    out: list[NormalizedMedicalDocument] = []
    for d in docs:
        if d.id in seen_ids:
            continue
        u = (d.source_url or "").strip()
        if u and u in seen_urls:
            continue
        seen_ids.add(d.id)
        if u:
            seen_urls.add(u)
        out.append(d)
    return out


def format_live_reference_block(docs: list[NormalizedMedicalDocument]) -> str:
    """Human-readable block for the model; keep short to save tokens."""
    if not docs:
        return ""
    parts: list[str] = [
        "These snippets come from Orphadata (Orphanet, CC-BY-4.0) and/or MedlinePlus (NLM). "
        "They are reference summaries, not personalized medical advice. Prefer the TRUSTED_INDEXED_EVIDENCE "
        "block for trial/paper/regulatory citations when both are present."
    ]
    for i, d in enumerate(docs[:8], 1):
        body = (d.plain_language_summary or d.summary or "").strip()
        if len(body) > 700:
            body = body[:700].rsplit(" ", 1)[0] + "…"
        parts.append(
            f"[LIVE-{i}] {d.source_name}\n"
            f"Title: {d.title}\n"
            f"URL: {d.source_url}\n"
            f"Summary: {body}"
        )
    return "\n\n".join(parts)


async def fetch_live_normalized_documents(
    *,
    query: str,
    condition_name: str | None,
    intent: UserIntent,
    limit_per_provider: int = 5,
    db: Session | None = None,
) -> list[NormalizedMedicalDocument]:
    providers = providers_for_intent(intent)
    if db is not None:
        providers = filter_live_providers_by_source_enabled(db, providers)
    if not providers:
        return []

    async def run_one(p: MedicalIntelProvider) -> list[NormalizedMedicalDocument]:
        try:
            raws = await p.search(
                query,
                condition_hint=condition_name,
                intent=intent,
                limit=limit_per_provider,
            )
        except Exception:
            return []
        out: list[NormalizedMedicalDocument] = []
        for raw in raws:
            try:
                out.append(p.normalize(raw))
            except Exception:
                continue
        return out

    gathered = await asyncio.gather(*[run_one(p) for p in providers])
    flat: list[NormalizedMedicalDocument] = []
    for g in gathered:
        flat.extend(g)
    return _dedupe(flat)


def fetch_live_reference_block_sync(
    *,
    query: str,
    condition_name: str | None,
    intent: UserIntent,
    limit_per_provider: int = 5,
    db: Session | None = None,
) -> str:
    """Sync wrapper for FastAPI sync endpoints (runs a short async gather)."""
    docs = asyncio.run(
        fetch_live_normalized_documents(
            query=query,
            condition_name=condition_name,
            intent=intent,
            limit_per_provider=limit_per_provider,
            db=db,
        )
    )
    return format_live_reference_block(docs)
