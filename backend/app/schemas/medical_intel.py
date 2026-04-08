"""Unified document schema for multi-source medical intelligence (aggregation / ranking / answers).

Not persisted as its own table yet: use for in-memory pipelines and API responses alongside
existing ``ResearchItem`` rows. See ``app.services.medical_intel.bridge``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MedicalEntityType = Literal[
    "disease",
    "symptom",
    "treatment",
    "drug",
    "clinical_trial",
    "research_paper",
    "guideline",
    "safety_warning",
    "other",
]


class NormalizedMedicalDocument(BaseModel):
    """Single normalized item from any provider or legacy ingestion row."""

    id: str = Field(description="Stable id, e.g. research_item:<uuid> or orphanet:123")
    entity_type: MedicalEntityType = "other"
    title: str = ""
    source_name: str = ""
    source_url: str = ""
    summary: str = Field(default="", description="Short technical or source-native summary")
    plain_language_summary: str = Field(default="", description="Lay explanation when available")
    condition_name: str = Field(default="", description="Primary condition focus if known")
    keywords: list[str] = Field(default_factory=list)
    reliability_score: float = Field(default=0.85, ge=0.0, le=1.0, description="Source / editorial trust")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Query / intent match")
    freshness_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Recency normalized 0–1")
    published_at: datetime | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    internal_research_item_id: str | None = Field(
        default=None,
        description="When bridged from DB, original ResearchItem UUID string",
    )
