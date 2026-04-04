import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.adapters.base import SourceAdapter


def _parse_iso_date(value: Any) -> datetime:
    if isinstance(value, str) and value:
        try:
            if len(value) == 10:
                return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)


def _safe_get(d: dict, path: list[str]) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


class ClinicalTrialsAdapter(SourceAdapter):
    name = "ClinicalTrials.gov"

    async def fetch_updates(self, condition_name: str) -> list[dict[str, Any]]:
        # ClinicalTrials.gov API v2 uses token pagination.
        url = f"{settings.clinical_trials_base_url}/studies"
        params: dict[str, Any] = {"query.cond": condition_name, "pageSize": 20, "format": "json"}

        headers = {
            # Some APIs are picky about user-agent; include a stable UA.
            "User-Agent": f"{settings.ncbi_tool_name or 'CureCompass'}/ingestion",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=40.0, headers=headers) as client:
            try:
                r = await client.get(url, params=params)
                r.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # ClinicalTrials.gov can return 403 in some environments; don't fail the whole ingestion run.
                if exc.response.status_code == 403:
                    return []
                raise
            data = r.json()

        studies: list[dict[str, Any]] = data.get("studies") or data.get("study") or []
        out: list[dict[str, Any]] = []

        for s in studies:
            protocol = s.get("protocolSection") or {}
            ident = protocol.get("identificationModule") or {}
            nct_id = ident.get("nctId")
            title = ident.get("briefTitle") or ""
            status = _safe_get(protocol, ["statusModule", "overallStatus"]) or ""
            phase_val = _safe_get(protocol, ["designModule", "phases"]) or []
            phase = ",".join([str(x) for x in phase_val]) if isinstance(phase_val, list) else str(phase_val or "")

            overall = s.get("protocolSection", {}).get("statusModule", {}).get("overallStatus", "")
            if not status and overall:
                status = overall

            # Interventions
            interventions_mod = protocol.get("armsInterventionsModule") or {}
            interventions = interventions_mod.get("interventions") or []
            intervention_text_parts: list[str] = []
            for it in interventions:
                if isinstance(it, dict):
                    name = it.get("interventionName") or it.get("interventionType") or ""
                    if name:
                        intervention_text_parts.append(str(name))
            intervention_text = ", ".join(intervention_text_parts)

            # Eligibility
            eligibility_mod = protocol.get("eligibilityModule") or {}
            eligibility_criteria = eligibility_mod.get("eligibilityCriteria") or ""

            # Some responses are extremely long; keep a short snippet.
            eligibility_summary = str(eligibility_criteria)[:1500] if eligibility_criteria else ""

            min_age = eligibility_mod.get("minimumAge") or None
            max_age = eligibility_mod.get("maximumAge") or None

            def _age_value(age_obj: Any) -> int | None:
                if isinstance(age_obj, dict):
                    v = age_obj.get("value")
                    if isinstance(v, (int, float, str)):
                        try:
                            return int(float(v))
                        except ValueError:
                            return None
                return None

            age_min = _age_value(min_age)
            age_max = _age_value(max_age)

            sex = eligibility_mod.get("gender") or eligibility_mod.get("sex") or "all"
            if isinstance(sex, dict):
                sex = sex.get("label") or "all"

            # Locations
            loc_mod = protocol.get("contactsLocationsModule") or {}
            locations = loc_mod.get("locations") or []
            countries: list[Any] = []
            locations_json: list[Any] = []
            for loc in locations:
                if not isinstance(loc, dict):
                    continue
                locations_json.append(
                    {
                        "facility": loc.get("facility") or {},
                        "city": loc.get("city") or "",
                        "state": loc.get("state") or "",
                        "country": loc.get("country") or "",
                    }
                )
                c = loc.get("country")
                if c:
                    countries.append(c)

            # Outcomes (best-effort)
            outcome_mod = protocol.get("outcomeMeasuresModule") or {}
            primary_measures = outcome_mod.get("primaryOutcomeMeasures") or []
            primary_endpoint = ""
            if isinstance(primary_measures, list) and primary_measures:
                first = primary_measures[0]
                if isinstance(first, dict):
                    primary_endpoint = first.get("measure") or first.get("description") or ""
                elif isinstance(first, str):
                    primary_endpoint = first
            primary_endpoint = str(primary_endpoint)[:600]

            # Dates
            published_at = (
                s.get("lastUpdatePostDate")
                or s.get("firstPostDate")
                or _safe_get(protocol, ["identificationModule", "studyFirstPostDate"])
                or _safe_get(ident, ["studyFirstPostDate"])
                or _parse_iso_date(None)
            )
            published_dt = _parse_iso_date(published_at)

            if not nct_id:
                continue

            # Normalize into a ResearchItem + nested trial dict.
            out.append(
                {
                    "external_id": str(nct_id),
                    "item_type": "trial",
                    "title": title or str(nct_id),
                    "abstract_or_body": eligibility_summary,
                    "source_url": f"https://clinicaltrials.gov/study/{nct_id}",
                    "published_at": published_dt.isoformat(),
                    "trial": {
                        "status": status or "",
                        "phase": phase or "",
                        "title": title or "",
                        "intervention": intervention_text or "",
                        "eligibility_summary": eligibility_summary,
                        "age_min": age_min,
                        "age_max": age_max,
                        "sex": str(sex or "all"),
                        "countries_json": countries,
                        "locations_json": locations_json,
                        "primary_endpoint": primary_endpoint,
                        "primary_endpoint_plain_language": primary_endpoint,
                    },
                }
            )

            # Gentle throttle
            await asyncio.sleep(0.05)

        return out

    def normalize(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        return raw_item

    def dedupe_key(self, normalized_item: dict[str, Any]) -> str:
        return str(normalized_item.get("external_id", ""))
