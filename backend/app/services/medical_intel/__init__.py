"""Medical intelligence: intents, trust, live providers (Orphadata, MedlinePlus), bridges to ingestion."""

from app.services.medical_intel.aggregation import (
    AggregationResult,
    aggregate_and_rank,
    build_legacy_normalized_documents,
    dedupe_documents,
    format_aggregated_evidence_for_prompt,
)
from app.services.medical_intel.bridge import research_item_to_normalized
from app.services.medical_intel.intent import UserIntent, infer_intent_heuristic
from app.services.medical_intel.orchestrator import (
    fetch_live_normalized_documents,
    fetch_live_reference_block_sync,
    format_live_reference_block,
)
from app.services.medical_intel.provider import MedicalIntelProvider
from app.services.medical_intel.registry import (
    ensure_builtin_providers_registered,
    filter_live_providers_by_source_enabled,
    providers_for_intent,
)
from app.services.medical_intel.safety import medical_attention_hints
from app.services.medical_intel.trust import default_reliability_for_source_name, trust_tier_for_source_name

__all__ = [
    "AggregationResult",
    "aggregate_and_rank",
    "build_legacy_normalized_documents",
    "dedupe_documents",
    "format_aggregated_evidence_for_prompt",
    "MedicalIntelProvider",
    "UserIntent",
    "infer_intent_heuristic",
    "default_reliability_for_source_name",
    "trust_tier_for_source_name",
    "research_item_to_normalized",
    "providers_for_intent",
    "filter_live_providers_by_source_enabled",
    "ensure_builtin_providers_registered",
    "fetch_live_normalized_documents",
    "fetch_live_reference_block_sync",
    "format_live_reference_block",
    "medical_attention_hints",
]
