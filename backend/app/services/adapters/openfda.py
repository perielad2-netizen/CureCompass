import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.services.adapters.base import SourceAdapter


class OpenFDAAdapter(SourceAdapter):
    name = "openFDA"

    async def fetch_updates(self, condition_name: str) -> list[dict[str, Any]]:
        # Best-effort: openFDA label search by condition term.
        # Note: this is not condition→specific label mapping; AI will later contextualize.
        if not settings.openfda_base_url:
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{settings.openfda_base_url}/drug/label.json",
                params={"search": condition_name, "limit": 10},
            )
            r.raise_for_status()
            data = r.json()
            results: list[dict[str, Any]] = data.get("results") or []
            out: list[dict[str, Any]] = []

            for item in results:
                set_id = item.get("set_id")
                if not set_id:
                    continue
                openfda = item.get("openfda") or {}
                brand = openfda.get("brand_name") or []
                brand_name = brand[0] if isinstance(brand, list) and brand else (brand if isinstance(brand, str) else "")

                effective_time = item.get("effective_time") or item.get("submission_date") or ""
                published_at = None
                if isinstance(effective_time, str) and len(effective_time) >= 8 and effective_time.isdigit():
                    # YYYYMMDD
                    try:
                        dt = datetime.strptime(effective_time[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
                        published_at = dt.isoformat()
                    except ValueError:
                        published_at = None

                text = item.get("spl_content") or ""
                if not isinstance(text, str):
                    text = ""

                out.append(
                    {
                        "external_id": str(set_id),
                        "item_type": "regulatory",
                        "title": brand_name or f"openFDA label {set_id}",
                        "abstract_or_body": text[:3000],
                        "source_url": "https://open.fda.gov/apis/",
                        "published_at": published_at,
                    }
                )
                await asyncio.sleep(0.02)

            return out

    def normalize(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        return raw_item

    def dedupe_key(self, normalized_item: dict[str, Any]) -> str:
        return str(normalized_item.get("external_id", ""))
