import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.adapters.base import SourceAdapter


class PubMedAdapter(SourceAdapter):
    name = "PubMed"

    NCBI_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    async def fetch_updates(self, condition_name: str) -> list[dict[str, Any]]:
        # E-utilities recommended params: tool and email
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": condition_name,
            "retmode": "json",
            "retmax": 20,
            "sort": "pubdate",
        }
        if settings.ncbi_api_key:
            params["api_key"] = settings.ncbi_api_key
        if settings.ncbi_tool_name:
            params["tool"] = settings.ncbi_tool_name
        if settings.ncbi_contact_email:
            params["email"] = settings.ncbi_contact_email

        async with httpx.AsyncClient(timeout=30.0) as client:
            esearch = await self._esearch_json(client, params)
            pmids = esearch.get("esearchresult", {}).get("idlist", [])
            if not pmids:
                return []

            # Fetch in a small batch to keep request size reasonable.
            # efetch supports comma-separated ids.
            efetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids[:20]),
                "retmode": "xml",
                "rettype": "abstract",
            }
            if settings.ncbi_api_key:
                efetch_params["api_key"] = settings.ncbi_api_key
            if settings.ncbi_tool_name:
                efetch_params["tool"] = settings.ncbi_tool_name
            if settings.ncbi_contact_email:
                efetch_params["email"] = settings.ncbi_contact_email

            xml_text = await self._efetch_xml(client, efetch_params)
            return self._parse_efetch_xml(xml_text)

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.HTTPError,)),
    )
    async def _esearch_json(self, client: httpx.AsyncClient, params: dict[str, Any]) -> dict[str, Any]:
        r = await client.get(self.NCBI_ESEARCH_URL, params=params)
        r.raise_for_status()
        return r.json()

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.HTTPError,)),
    )
    async def _efetch_xml(self, client: httpx.AsyncClient, params: dict[str, Any]) -> str:
        r = await client.get(self.NCBI_EFETCH_URL, params=params)
        r.raise_for_status()
        # NCBI returns xml
        await asyncio.sleep(0.1)
        return r.text

    def _parse_efetch_xml(self, xml_text: str) -> list[dict[str, Any]]:
        # Minimal, robust XML parsing for title + abstract + pub date + PMID.
        # This is intentionally tolerant: missing fields won’t break ingestion.
        root = ElementTree.fromstring(xml_text)
        # namespace-free access is tricky; use .find with wildcard-ish by searching tags.
        results: list[dict[str, Any]] = []

        for article in root.findall(".//PubmedArticle"):
            pmid = None
            title = ""
            abstract = ""
            published_at: str | None = None

            # PMID
            pmid_el = article.find(".//MedlineCitation/PMID")
            if pmid_el is not None and pmid_el.text:
                pmid = pmid_el.text.strip()

            # Title
            title_el = article.find(".//ArticleTitle")
            if title_el is not None and title_el.text:
                title = re.sub(r"\\s+", " ", title_el.text).strip()

            # Abstract (may be split into sections)
            abstract_parts: list[str] = []
            abstract_el = article.find(".//Abstract")
            if abstract_el is not None:
                for p in abstract_el.findall(".//AbstractText"):
                    txt = "".join(p.itertext()).strip()
                    if txt:
                        abstract_parts.append(txt)
            abstract = " ".join(abstract_parts).strip()

            # Date (Year/Month/Day)
            pub_date_el = article.find(".//PubDate")
            if pub_date_el is not None:
                year = pub_date_el.findtext("Year")
                month = pub_date_el.findtext("Month")
                day = pub_date_el.findtext("Day")
                if year:
                    y = int(year)
                    m = int(month) if month and month.isdigit() else 1
                    d = int(day) if day and day.isdigit() else 1
                    dt = datetime(y, m, d, tzinfo=timezone.utc)
                    published_at = dt.isoformat()

            if not pmid:
                continue

            results.append(
                {
                    "external_id": pmid,
                    "item_type": "paper",
                    "title": title,
                    "abstract_or_body": abstract,
                    "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "published_at": published_at,
                }
            )

        return results

    def normalize(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        # Raw already normalized enough for our internal ResearchItem shape.
        return raw_item

    def dedupe_key(self, normalized_item: dict[str, Any]) -> str:
        return str(normalized_item.get("external_id", ""))
