from enum import Enum

from pydantic import BaseModel, Field

from app.services.schemas import EvidenceClassification


class HypeRisk(str, Enum):
    very_early_data = "very_early_data"
    animal_only_evidence = "animal_only_evidence"
    no_human_efficacy_evidence = "no_human_efficacy_evidence"
    hypothesis_generating_only = "hypothesis_generating_only"
    approved_and_available_now = "approved_and_available_now"
    promising_but_uncertain = "promising_but_uncertain"


class ResearchItemEnrichmentOut(BaseModel):
    lay_summary: str = Field(min_length=40)
    clinician_summary: str = Field(min_length=40)
    why_it_matters: str = Field(min_length=20)

    evidence_stage: EvidenceClassification
    confidence_level: str = Field(pattern="^(low|medium|high)$")
    hype_risk: HypeRisk
    applicability_age_group: str = Field(pattern="^(pediatric|adult|both|unknown)$")

    availability: str = Field(pattern="^(available_now|still_experimental|unknown)$")

    relevance_score: float = Field(ge=0, le=1)
    novelty_score: float = Field(ge=0, le=1)
    actionability_score: float = Field(ge=0, le=1)


class EnrichConditionIn(BaseModel):
    condition_slug: str = Field(min_length=2, max_length=64)
    # Optional cap for development/testing.
    limit: int | None = Field(default=None, ge=1, le=200)

