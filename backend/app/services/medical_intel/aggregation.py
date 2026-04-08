"""Merge, dedupe, and rank ``NormalizedMedicalDocument`` lists (indexed + live providers)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ResearchItem, ResearchItemAI, Source
from app.schemas.medical_intel import MedicalEntityType, NormalizedMedicalDocument
from app.services.medical_intel.bridge import research_item_to_normalized
from app.services.medical_intel.intent import UserIntent
from app.services.medical_intel.trust import trust_tier_for_source_name

NCT_RE = re.compile(r"NCT\d{8}", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

# Composite ranking weights (sum ≈ 1.0 before evidence_kind)
W_TRUST = 0.26
W_RELEVANCE = 0.22
W_FRESHNESS = 0.12
W_INTENT_ENTITY = 0.14
W_TITLE_QUERY = 0.18
W_EVIDENCE_KIND = 0.08


@dataclass
class AggregationResult:
    documents: list[NormalizedMedicalDocument]
    legacy_count: int
    live_count: int
    duplicates_removed: int
    used_fallback: bool
    top_source_names: list[str] = field(default_factory=list)


def canonical_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    p = urlparse(u.lower())
    netloc = (p.netloc or "").split("@")[-1]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = (p.path or "").rstrip("/") or ""
    # Drop common tracking params
    q = parse_qs(p.query, keep_blank_values=False)
    for drop in list(q.keys()):
        if drop.lower() in ("utm_source", "utm_medium", "utm_campaign", "fbclid"):
            del q[drop]
    query = urlencode(sorted((k, v[0]) for k, v in q.items() if v), doseq=False)
    return urlunparse((p.scheme or "https", netloc, path, "", query, ""))


def nct_ids_from_text(*parts: str) -> frozenset[str]:
    bag: set[str] = set()
    for p in parts:
        if not p:
            continue
        bag.update(m.group(0).upper() for m in NCT_RE.finditer(p))
    return frozenset(bag)


def _norm_title(t: str) -> str:
    return " ".join(_TOKEN_RE.findall((t or "").lower()))


def title_similarity(a: str, b: str) -> float:
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def external_id_key(doc: NormalizedMedicalDocument) -> str | None:
    raw = doc.raw_data or {}
    ext = raw.get("external_id")
    if ext and str(ext).strip():
        return f"{doc.source_name.lower()}::{str(ext).strip().lower()}"
    return None


def _trial_conflict(a: NormalizedMedicalDocument, b: NormalizedMedicalDocument) -> bool:
    """If both look like trials but reference different NCT IDs, do not treat as duplicate."""
    if a.entity_type != "clinical_trial" or b.entity_type != "clinical_trial":
        return False
    na = nct_ids_from_text(a.title, a.source_url, a.summary)
    nb = nct_ids_from_text(b.title, b.source_url, b.summary)
    if na and nb and na.isdisjoint(nb):
        return True
    return False


def dedupe_documents(documents: list[NormalizedMedicalDocument]) -> tuple[list[NormalizedMedicalDocument], int]:
    """Conservative dedupe: id, canonical URL, external_id+source, fuzzy title + entity (not across conflicting trials)."""
    kept: list[NormalizedMedicalDocument] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    seen_ext: set[str] = set()
    removed = 0

    for doc in documents:
        cid = (doc.id or "").strip()
        if cid and cid in seen_ids:
            removed += 1
            continue
        cu = canonical_url(doc.source_url)
        if cu and cu in seen_urls:
            removed += 1
            continue
        ek = external_id_key(doc)
        if ek and ek in seen_ext:
            removed += 1
            continue

        dup_fuzzy = False
        for k in kept:
            if title_similarity(doc.title, k.title) >= 0.9 and doc.entity_type == k.entity_type:
                if _trial_conflict(doc, k):
                    continue
                cond_a = (doc.condition_name or "").strip().lower()
                cond_b = (k.condition_name or "").strip().lower()
                if not cond_a or not cond_b or cond_a == cond_b:
                    dup_fuzzy = True
                    break
        if dup_fuzzy:
            removed += 1
            continue

        if cid:
            seen_ids.add(cid)
        if cu:
            seen_urls.add(cu)
        if ek:
            seen_ext.add(ek)
        kept.append(doc)

    return kept, removed


def _tokens(s: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((s or "").lower()) if len(t) > 2}


def title_query_overlap(query: str, title: str) -> float:
    q, t = _tokens(query), _tokens(title)
    if not q or not t:
        return 0.35
    inter = len(q & t)
    union = len(q | t) or 1
    return max(0.0, min(1.0, inter / union))


def intent_entity_alignment(intent: UserIntent, entity: MedicalEntityType) -> float:
    m: dict[UserIntent, tuple[MedicalEntityType, ...]] = {
        UserIntent.clinical_trials: ("clinical_trial",),
        UserIntent.latest_research: ("research_paper", "clinical_trial"),
        UserIntent.drug_info: ("drug", "treatment", "safety_warning"),
        UserIntent.side_effects: ("safety_warning", "drug"),
        UserIntent.genetics: ("disease",),
        UserIntent.symptoms: ("disease", "symptom"),
        UserIntent.treatment: ("treatment", "clinical_trial", "drug", "guideline"),
        UserIntent.prognosis: ("disease", "research_paper"),
        UserIntent.disease_overview: ("disease", "research_paper", "other"),
        UserIntent.daily_life_help: ("disease", "guideline", "other"),
        UserIntent.urgent_warning: ("safety_warning", "disease", "guideline"),
        UserIntent.unknown: tuple(),
    }
    preferred = m.get(intent, tuple())
    if not preferred:
        return 0.72
    return 1.0 if entity in preferred else 0.55


def evidence_kind_boost(entity: MedicalEntityType) -> float:
    return {
        "clinical_trial": 1.0,
        "research_paper": 0.96,
        "safety_warning": 0.94,
        "guideline": 0.93,
        "treatment": 0.9,
        "drug": 0.9,
        "disease": 0.86,
        "symptom": 0.84,
        "other": 0.8,
    }.get(entity, 0.8)


def trust_weight_from_doc(doc: NormalizedMedicalDocument) -> float:
    tier = trust_tier_for_source_name(doc.source_name)
    base = float(doc.reliability_score or 0.8)
    if tier == "high":
        return min(1.0, base * 1.02)
    if tier == "medium":
        return base
    return base * 0.92


def composite_rank_score(
    doc: NormalizedMedicalDocument,
    *,
    user_query: str,
    intent: UserIntent,
) -> float:
    trust = trust_weight_from_doc(doc)
    rel = max(0.0, min(1.0, doc.relevance_score))
    fresh = max(0.0, min(1.0, doc.freshness_score))
    intent_e = intent_entity_alignment(intent, doc.entity_type)
    tq = title_query_overlap(user_query, doc.title)
    ek = evidence_kind_boost(doc.entity_type)
    return (
        W_TRUST * trust
        + W_RELEVANCE * rel
        + W_FRESHNESS * fresh
        + W_INTENT_ENTITY * intent_e
        + W_TITLE_QUERY * tq
        + W_EVIDENCE_KIND * ek
    )


def aggregate_and_rank(
    legacy_docs: list[NormalizedMedicalDocument],
    live_docs: list[NormalizedMedicalDocument],
    *,
    user_query: str,
    intent: UserIntent,
    condition_name: str = "",
) -> AggregationResult:
    """Concatenate legacy first (priority), then live; dedupe; rank by composite score."""
    _ = condition_name
    merged = list(legacy_docs) + list(live_docs)
    deduped, n_dup = dedupe_documents(merged)
    scored = [(composite_rank_score(d, user_query=user_query, intent=intent), d) for d in deduped]
    scored.sort(key=lambda x: x[0], reverse=True)
    final = [d for _, d in scored]
    top_names: list[str] = []
    seen_n: set[str] = set()
    for d in final[:8]:
        n = (d.source_name or "").strip()
        if n and n not in seen_n:
            seen_n.add(n)
            top_names.append(n)
    return AggregationResult(
        documents=final,
        legacy_count=len(legacy_docs),
        live_count=len(live_docs),
        duplicates_removed=n_dup,
        used_fallback=False,
        top_source_names=top_names,
    )


def format_aggregated_evidence_for_prompt(documents: list[NormalizedMedicalDocument], *, max_items: int = 8) -> str:
    """Structured block for the LLM; preserve research_item_id for citation rules."""
    lines: list[str] = []
    for i, d in enumerate(documents[:max_items], 1):
        rid = d.internal_research_item_id or ""
        id_line = f"research_item_id={rid}" if rid else "research_item_id=(none — reference URL only)"
        body = (d.plain_language_summary or d.summary or "")[:2000]
        lines.append(
            f"--- Item {i} ---\n"
            f"{id_line}\n"
            f"Source: {d.source_name}\n"
            f"Entity: {d.entity_type}\n"
            f"Title: {d.title}\n"
            f"URL: {d.source_url}\n"
            f"Published: {d.published_at.isoformat() if d.published_at else ''}\n"
            f"Trust_hint: {d.reliability_score:.2f}\n"
            f"Body: {body}"
        )
    return "\n\n".join(lines)


def build_legacy_normalized_documents(
    db: Session,
    research_docs: list[dict[str, Any]],
    *,
    condition_name: str,
    answer_lang: str,
) -> list[NormalizedMedicalDocument]:
    """Load ORM rows for retrieval dicts (order preserved) and bridge to normalized schema."""
    ids: list[UUID] = []
    for d in research_docs:
        try:
            ids.append(UUID(str(d["research_item_id"])))
        except (KeyError, ValueError, TypeError):
            continue
    if not ids:
        return []

    stmt = (
        select(ResearchItem, Source, ResearchItemAI)
        .join(Source, Source.id == ResearchItem.source_id)
        .join(ResearchItemAI, ResearchItemAI.research_item_id == ResearchItem.id, isouter=True)
        .where(ResearchItem.id.in_(ids))
    )
    rows = db.execute(stmt).all()
    by_id: dict[str, tuple[ResearchItem, Source, ResearchItemAI | None]] = {}
    for item, source, ai in rows:
        by_id[str(item.id)] = (item, source, ai)

    out: list[NormalizedMedicalDocument] = []
    for d in research_docs:
        rid = str(d.get("research_item_id") or "")
        if rid not in by_id:
            continue
        item, source, ai = by_id[rid]
        lay = ""
        if ai:
            if answer_lang == "he" and (ai.lay_summary_he or "").strip():
                lay = (ai.lay_summary_he or "").strip()
            else:
                lay = (ai.lay_summary or "").strip()
            if answer_lang == "he" and not lay:
                lay = (ai.lay_summary or "").strip()
        rank = int(d.get("retrieval_rank", len(out)))
        rel = max(0.35, min(0.96, 0.94 - rank * 0.11))
        out.append(
            research_item_to_normalized(
                item,
                source,
                plain_language_summary=lay[:4000],
                condition_name=condition_name,
                relevance_score=rel,
            )
        )
    return out
