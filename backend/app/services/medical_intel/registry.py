"""Provider registry and intent → provider routing (Phase 2+ will register instances)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Source
from app.services.medical_intel.intent import UserIntent
from app.services.medical_intel.provider import MedicalIntelProvider

# ``Source.name`` rows seeded in ``app.db.seed`` — must match live MedicalIntelProvider implementations.
LIVE_INTEL_SOURCE_NAME_BY_PROVIDER_ID: dict[str, str] = {
    "orphadata": "Orphanet (Orphadata)",
    "medlineplus_nlm": "MedlinePlus (NLM)",
}

_REGISTERED: list[MedicalIntelProvider] = []
_BOOTSTRAPPED = False

# Rare-disease reference: Orphadata for these intents.
_ORPHADATA_INTENTS: frozenset[str] = frozenset(
    {
        "disease_overview",
        "genetics",
        "prognosis",
        "unknown",
        "daily_life_help",
        "symptoms",
        "treatment",
        "urgent_warning",
    }
)
# ClinicalTrials.gov already ingested; skip live consumer-health search for this intent only.
_SKIP_MEDLINE_INTENTS: frozenset[str] = frozenset({"clinical_trials"})


def register_provider(provider: MedicalIntelProvider) -> None:
    """Idempotent registration for app startup or tests."""
    if any(p.provider_id == provider.provider_id for p in _REGISTERED):
        return
    _REGISTERED.append(provider)


def registered_providers() -> list[MedicalIntelProvider]:
    return list(_REGISTERED)


def ensure_builtin_providers_registered() -> None:
    """Load Orphadata + MedlinePlus providers once (no DB side effects)."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    from app.services.medical_intel.providers import MedlinePlusProvider, OrphadataProvider

    register_provider(OrphadataProvider())
    register_provider(MedlinePlusProvider())
    _BOOTSTRAPPED = True


def providers_for_intent(intent: UserIntent) -> list[MedicalIntelProvider]:
    """Return providers to query for this intent."""
    ensure_builtin_providers_registered()
    key = intent.value
    by_id = {p.provider_id: p for p in _REGISTERED}
    out: list[MedicalIntelProvider] = []

    if key in _ORPHADATA_INTENTS and "orphadata" in by_id:
        out.append(by_id["orphadata"])
    if key not in _SKIP_MEDLINE_INTENTS and "medlineplus_nlm" in by_id:
        out.append(by_id["medlineplus_nlm"])
    return out


def filter_live_providers_by_source_enabled(
    db: Session, providers: list[MedicalIntelProvider]
) -> list[MedicalIntelProvider]:
    """Drop live providers whose matching ``Source`` row exists in the DB and has ``enabled=False``.

    If a mapped ``Source`` row is missing (e.g. before seed), the provider is still allowed so environments
    without reference rows are not broken.
    """
    if not providers:
        return []
    names = {LIVE_INTEL_SOURCE_NAME_BY_PROVIDER_ID.get(p.provider_id) for p in providers}
    names.discard(None)
    if not names:
        return providers
    rows = db.execute(select(Source.name, Source.enabled).where(Source.name.in_(names))).all()
    enabled_by_name: dict[str, bool] = {str(r[0]): bool(r[1]) for r in rows}
    out: list[MedicalIntelProvider] = []
    for p in providers:
        mapped = LIVE_INTEL_SOURCE_NAME_BY_PROVIDER_ID.get(p.provider_id)
        if mapped is None:
            out.append(p)
            continue
        if mapped not in enabled_by_name:
            out.append(p)
            continue
        if enabled_by_name[mapped]:
            out.append(p)
    return out
