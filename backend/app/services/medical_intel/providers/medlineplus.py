"""MedlinePlus health topics via NLM wsearch (XML). Respect ~85 req/min per IP; cache at CDN/proxy if scaling."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import settings
from app.schemas.medical_intel import NormalizedMedicalDocument
from app.services.medical_intel.intent import UserIntent
from app.services.medical_intel.provider import MedicalIntelProvider
from app.services.medical_intel.trust import default_reliability_for_source_name

NLM_WSEARCH = "https://wsearch.nlm.nih.gov/ws/query"


def _strip_html(s: str) -> str:
    t = re.sub(r"<[^>]+>", " ", s or "").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", t).strip()


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


class MedlinePlusProvider(MedicalIntelProvider):
    provider_id = "medlineplus_nlm"
    display_name = "MedlinePlus (NLM)"

    def _search_term(self, query: str, condition_hint: str | None) -> str:
        h = (condition_hint or "").strip()
        if h:
            return h[:200]
        q = (query or "").strip()
        return q[:200]

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

        params = {"db": "healthTopics", "term": term, "retmax": str(max(1, min(limit, 12)))}
        headers = {
            "User-Agent": f"{settings.ncbi_tool_name or 'CureCompass'}/1.0 (medical-intel; +{settings.ncbi_contact_email or 'https://github.com'})",
        }
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                r = await client.get(NLM_WSEARCH, params=params, headers=headers)
                r.raise_for_status()
                xml_text = r.text
        except (httpx.HTTPError, ValueError):
            return []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        out: list[dict[str, Any]] = []
        for doc in root.iter():
            if _local(doc.tag) != "document":
                continue
            url = (doc.get("url") or "").strip()
            if not url:
                continue
            title = ""
            snippet = ""
            full_summary = ""
            for child in doc:
                if _local(child.tag) != "content":
                    continue
                name = child.get("name")
                text = "".join(child.itertext()) if len(child) else (child.text or "")
                text = _strip_html(text)
                if name == "title":
                    title = text
                elif name == "snippet":
                    snippet = text
                elif name == "FullSummary":
                    full_summary = text
            body = snippet or full_summary[:1200]
            if not title:
                title = url.rsplit("/", 1)[-1].replace(".html", "").replace("-", " ")
            out.append(
                {
                    "_provider": self.provider_id,
                    "url": url,
                    "title": title,
                    "snippet": body[:2500],
                }
            )
            if len(out) >= max(1, min(limit, 12)):
                break
        return out

    def normalize(self, raw: dict[str, Any]) -> NormalizedMedicalDocument:
        url = (raw.get("url") or "").strip()
        title = (raw.get("title") or "MedlinePlus topic").strip()
        snippet = (raw.get("snippet") or "").strip()
        rel = default_reliability_for_source_name("MedlinePlus")
        slug = quote_plus(url)[:80]
        return NormalizedMedicalDocument(
            id=f"medlineplus:{slug}",
            entity_type="disease",
            title=title,
            source_name=self.display_name,
            source_url=url,
            summary=snippet[:4000],
            plain_language_summary=(snippet[:900] + "…") if len(snippet) > 900 else snippet,
            condition_name=title,
            keywords=[],
            reliability_score=rel,
            relevance_score=0.72,
            freshness_score=0.9,
            published_at=None,
            raw_data=raw,
        )
