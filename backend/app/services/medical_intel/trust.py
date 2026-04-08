"""Default trust / reliability for known source display names (seed + future providers)."""

from __future__ import annotations

from typing import Literal

TrustTier = Literal["high", "medium", "low"]

# Planned / external sources (used when those providers land). Aliases lowercased.
_HIGH = frozenset(
    {
        "fda",
        "openfda",
        "ema",
        "who",
        "cdc",
        "nhs",
        "orphanet",
        "gard",
        "genetic and rare diseases",
        "medlineplus",
        "medline plus",
    }
)
_MEDIUM = frozenset(
    {
        "pubmed",
        "clinicaltrials.gov",
        "clinicaltrials",
    }
)

_HIGH_TRUST_SCORE = 0.95
_MEDIUM_TRUST_SCORE = 0.88
_LOW_TRUST_SCORE = 0.75


def trust_tier_for_source_name(source_name: str) -> TrustTier:
    key = (source_name or "").strip().lower()
    if not key:
        return "low"
    if key in _HIGH or any(h in key for h in ("orphanet", "gard", "medline", "nhs", "who", "cdc", "ema", "fda")):
        return "high"
    if key in _MEDIUM or any(m in key for m in ("pubmed", "clinicaltrials")):
        return "medium"
    return "low"


def default_reliability_for_source_name(source_name: str) -> float:
    tier = trust_tier_for_source_name(source_name)
    if tier == "high":
        return _HIGH_TRUST_SCORE
    if tier == "medium":
        return _MEDIUM_TRUST_SCORE
    return _LOW_TRUST_SCORE
