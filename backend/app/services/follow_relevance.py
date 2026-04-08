"""Personalize research and trials using follow preferences (age scope, geography).

Inference order for each item:
1. ``ResearchItemAI.applicability_age_group`` when not ``unknown``
2. Linked ``Trial`` age bounds (same logic as ClinicalTrials.gov eligibility)
3. ``normalized_metadata_json["trial"]`` age bounds when present
4. Light text heuristic for papers (PubMed, etc.) without enrichment
"""

from __future__ import annotations

import re
from typing import Any

from app.models.entities import ResearchItem, ResearchItemAI, Trial

Audience = str  # pediatric | adult | both | unknown

_PED_WORDS = re.compile(
    r"\b(pediatric|paediatric|children|childhood|child\s|infants?|neonatal|neonate|"
    r"adolescents?|school-?age|boys\s+and\s+girls|girls\s+and\s+boys|toddlers?)\b",
    re.I,
)
_ADULT_WORDS = re.compile(r"\b(adults?\s+with|elderly|geriatric|middle-?aged\s+adults?)\b", re.I)


def normalize_user_age_scope(raw: str | None) -> str:
    if not raw:
        return "both"
    v = raw.strip().lower()
    if v in ("pediatric", "adult", "both"):
        return v
    return "both"


def audience_from_trial_ages(age_min: int | None, age_max: int | None) -> Audience:
    """Map trial eligibility ages to a coarse audience label."""
    if age_min is None and age_max is None:
        return "unknown"
    mn = int(age_min) if age_min is not None else 0
    mx = int(age_max) if age_max is not None else 120
    if mx <= 17:
        return "pediatric"
    if mn >= 18:
        return "adult"
    return "both"


def _meta_trial(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    t = meta.get("trial")
    return t if isinstance(t, dict) else {}


def infer_item_audience(
    item: ResearchItem,
    ai: ResearchItemAI | None,
    trial: Trial | None,
) -> Audience:
    if ai and (ai.applicability_age_group or "").strip() not in ("", "unknown"):
        return str(ai.applicability_age_group).strip()

    if trial is not None:
        return audience_from_trial_ages(trial.age_min, trial.age_max)

    mt = _meta_trial(item.normalized_metadata_json if isinstance(item.normalized_metadata_json, dict) else {})
    if mt:
        am = mt.get("age_min")
        ax = mt.get("age_max")
        if am is not None or ax is not None:
            try:
                ami = int(am) if am is not None else None
                axi = int(ax) if ax is not None else None
            except (TypeError, ValueError):
                ami, axi = None, None
            else:
                return audience_from_trial_ages(ami, axi)

    text = f"{item.title or ''}\n{item.abstract_or_body or ''}"
    ped = bool(_PED_WORDS.search(text))
    ad = bool(_ADULT_WORDS.search(text))
    if ped and not ad:
        return "pediatric"
    if ad and not ped:
        return "adult"
    if ped and ad:
        return "both"
    return "unknown"


def audience_preference_multiplier(user_scope: str, item_audience: Audience) -> float:
    """Scale retrieval / ranking scores: downrank mismatched cohorts, uprank matches."""
    us = normalize_user_age_scope(user_scope)
    ia = item_audience if item_audience in ("pediatric", "adult", "both", "unknown") else "unknown"

    if us == "both":
        if ia == "unknown":
            return 1.0
        return 1.04

    if ia == "unknown":
        return 1.0
    if ia == "both":
        return 1.1
    if ia == us:
        return 1.22

    # Mismatch: adult-only work for a pediatric-only follow (or the reverse).
    return 0.18


def _flatten_countries_from_trial_dict(t: dict[str, Any]) -> list[str]:
    out: list[str] = []
    cj = t.get("countries_json")
    if isinstance(cj, list):
        out.extend(str(c) for c in cj if c)
    locs = t.get("locations_json")
    if isinstance(locs, list):
        for loc in locs:
            if isinstance(loc, dict):
                c = loc.get("country")
                if c:
                    out.append(str(c))
    return out


def countries_for_trial_row(trial: Trial) -> list[str]:
    """Site countries for geography boosting (mirrors ``countries_for_item`` for standalone trials)."""
    countries: list[str] = []
    if isinstance(trial.countries_json, list):
        countries.extend(str(c) for c in trial.countries_json if c)
    if isinstance(trial.locations_json, list):
        for loc in trial.locations_json:
            if isinstance(loc, dict) and loc.get("country"):
                countries.append(str(loc["country"]))
    return countries


def countries_for_item(item: ResearchItem, trial: Trial | None) -> list[str]:
    if trial is not None and isinstance(trial.countries_json, list):
        base = [str(c) for c in trial.countries_json if c]
        if isinstance(trial.locations_json, list):
            for loc in trial.locations_json:
                if isinstance(loc, dict) and loc.get("country"):
                    base.append(str(loc["country"]))
        if base:
            return base

    mt = _meta_trial(item.normalized_metadata_json if isinstance(item.normalized_metadata_json, dict) else {})
    return _flatten_countries_from_trial_dict(mt)


def geography_match_multiplier(user_geography: str | None, countries: list[str]) -> float:
    """Soft boost when trial/site countries align with the user's stated region."""
    if not user_geography:
        return 1.0
    u = user_geography.strip().lower()
    if u in ("", "global", "worldwide", "any", "international"):
        return 1.0

    # Hebrew / common aliases
    if "ישראל" in user_geography or u in ("israel", "il"):
        u_norm = "israel"
    elif u in ("usa", "us", "u.s.", "u.s.a.", "america"):
        u_norm = "united states"
    elif u in ("uk", "u.k.", "britain", "england", "scotland", "wales"):
        u_norm = "united kingdom"
    else:
        u_norm = u

    hay = " ".join(str(c).lower() for c in countries if c)
    if not hay.strip():
        return 1.0

    if u_norm in hay:
        return 1.12
    for c in countries:
        cl = str(c).lower()
        if len(u_norm) >= 3 and (u_norm in cl or cl in u_norm):
            return 1.12
    return 1.0


def combined_personalization_multiplier(
    *,
    user_age_scope: str | None,
    user_geography: str | None,
    item_audience: Audience,
    countries: list[str],
) -> float:
    return audience_preference_multiplier(user_age_scope or "both", item_audience) * geography_match_multiplier(
        user_geography, countries
    )
