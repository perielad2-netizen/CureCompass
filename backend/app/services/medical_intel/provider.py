"""Abstract provider for future API-based sources (Orphanet, GARD, …).

Existing ingestion uses ``SourceAdapter`` (condition-scoped fetch_updates). New providers
implement this interface for query-time or batch search without replacing adapters yet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.medical_intel.intent import UserIntent
    from app.schemas.medical_intel import NormalizedMedicalDocument


class MedicalIntelProvider(ABC):
    """One modular external source. Implement search + normalize; fetch_details optional."""

    provider_id: str
    display_name: str

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        condition_hint: str | None = None,
        intent: "UserIntent | None" = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return raw provider payloads (dicts). Orchestrator calls ``normalize`` on each."""

    async def fetch_details(self, external_id: str) -> dict[str, Any] | None:
        """Optional: single-record enrichment by provider id."""
        return None

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> "NormalizedMedicalDocument":
        """Map one raw dict to the shared schema."""
