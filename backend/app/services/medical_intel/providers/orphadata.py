"""Orphadata REST API (Orphanet rare-disease reference). CC-BY-4.0 — credit Orphanet/Orphadata."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.schemas.medical_intel import NormalizedMedicalDocument
from app.services.medical_intel.intent import UserIntent
from app.services.medical_intel.provider import MedicalIntelProvider
from app.services.medical_intel.trust import default_reliability_for_source_name

ORPHADATA_BASE = "https://api.orphadata.com"


def _is_obsolete(disorder: dict[str, Any]) -> bool:
    term = (disorder.get("Preferred term") or "").upper()
    if term.startswith("OBSOLETE"):
        return True
    flags = disorder.get("DisorderFlag") or []
    if isinstance(flags, dict):
        flags = [flags]
    for f in flags:
        if not isinstance(f, dict):
            continue
        lab = (f.get("Label") or "") or ""
        if "obsolete" in lab.lower() or "inactive" in lab.lower():
            return True
    return False


def _results_to_list(results: Any) -> list[dict[str, Any]]:
    if results is None:
        return []
    if isinstance(results, list):
        return [r for r in results if isinstance(r, dict)]
    if isinstance(results, dict):
        return [results]
    return []


class OrphadataProvider(MedicalIntelProvider):
    provider_id = "orphadata"
    display_name = "Orphanet (Orphadata)"

    def _search_term(self, query: str, condition_hint: str | None) -> str:
        h = (condition_hint or "").strip()
        if h:
            return h[:180]
        q = (query or "").strip()
        return q[:180]

    async def search(
        self,
        query: str,
        *,
        condition_hint: str | None = None,
        intent: UserIntent | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = intent
        term = self._search_term(query, condition_hint)
        if len(term) < 2:
            return []

        path = quote(term, safe="")
        url = f"{ORPHADATA_BASE}/rd-cross-referencing/orphacodes/names/{path}"
        headers = {
            "Accept": "application/json",
            "User-Agent": f"{settings.ncbi_tool_name or 'CureCompass'}/1.0 (medical-intel; +{settings.ncbi_contact_email or 'https://github.com'})",
        }
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                payload = r.json()
        except (httpx.HTTPError, ValueError):
            return []

        data = payload.get("data") or {}
        raw_list = _results_to_list(data.get("results"))
        out: list[dict[str, Any]] = []
        for d in raw_list:
            if _is_obsolete(d):
                continue
            out.append({"_provider": self.provider_id, "_orphadata_disorder": d})
            if len(out) >= max(1, min(limit, 10)):
                break
        return out

    async def fetch_details(self, external_id: str) -> dict[str, Any] | None:
        """external_id: ORPHAcode digits only."""
        code = (external_id or "").strip()
        if not code.isdigit():
            return None
        url = f"{ORPHADATA_BASE}/rd-cross-referencing/orphacodes/{code}"
        headers = {"Accept": "application/json", "User-Agent": settings.ncbi_tool_name or "CureCompass"}
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                payload = r.json()
        except (httpx.HTTPError, ValueError):
            return None
        data = (payload.get("data") or {}).get("results")
        if isinstance(data, dict):
            return {"_provider": self.provider_id, "_orphadata_disorder": data}
        return None

    def normalize(self, raw: dict[str, Any]) -> NormalizedMedicalDocument:
        disorder = raw.get("_orphadata_disorder") or {}
        orpha = disorder.get("ORPHAcode")
        orpha_s = str(orpha) if orpha is not None else ""
        title = (disorder.get("Preferred term") or "").strip() or "Rare disorder"
        url = (disorder.get("OrphanetURL") or "").strip() or f"https://www.orpha.net/en/disease/detail/{orpha_s}"
        syn = disorder.get("Synonym")
        keywords: list[str] = []
        if isinstance(syn, list):
            keywords = [str(x) for x in syn if x][:12]
        elif isinstance(syn, str) and syn:
            keywords = [syn]

        refs = disorder.get("ExternalReference") or []
        if isinstance(refs, dict):
            refs = [refs]
        ref_bits = []
        for ref in refs[:6]:
            if isinstance(ref, dict) and ref.get("Source") and ref.get("Reference"):
                ref_bits.append(f"{ref['Source']}: {ref['Reference']}")
        summary = " | ".join(ref_bits) if ref_bits else (disorder.get("Typology") or "") or ""
        plain = f"Orphanet rare disease entry: {title}. " + (
            f"Synonyms: {', '.join(keywords)}. " if keywords else ""
        )
        rel = default_reliability_for_source_name("Orphanet")
        return NormalizedMedicalDocument(
            id=f"orphadata:orpha:{orpha_s}" if orpha_s else f"orphadata:{hash(title)}",
            entity_type="disease",
            title=title,
            source_name=self.display_name,
            source_url=url,
            summary=summary[:2000],
            plain_language_summary=plain[:2000],
            condition_name=title,
            keywords=keywords,
            reliability_score=rel,
            relevance_score=0.75,
            freshness_score=0.85,
            published_at=None,
            raw_data=raw,
        )
