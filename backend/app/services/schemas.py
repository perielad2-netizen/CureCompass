from enum import Enum

from pydantic import BaseModel, Field


class EvidenceClassification(str, Enum):
    basic_research = "basic_research"
    animal_preclinical = "animal_preclinical"
    early_human_study = "early_human_study"
    phase_1 = "phase_1"
    phase_2 = "phase_2"
    phase_3 = "phase_3"
    results_posted = "results_posted"
    regulatory_review = "regulatory_review"
    approved_guideline_impacting = "approved_guideline_impacting"


class ResearchItemSummary(BaseModel):
    what_changed: str = Field(min_length=10)
    why_it_matters: str = Field(min_length=10)
    who_it_applies_to: str
    evidence_strength: EvidenceClassification
    availability: str
    confidence: str


class AskAIAnswer(BaseModel):
    direct_answer: str
    what_changed_recently: str
    evidence_strength: str
    available_now_or_experimental: str
    suggested_doctor_questions: list[str]
    sources: list[dict]
