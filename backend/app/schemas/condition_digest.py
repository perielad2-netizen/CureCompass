"""Structured output for AI-generated condition digests (OpenAI strict JSON schema)."""

from pydantic import BaseModel, ConfigDict, Field


class ConditionDigestItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=4, max_length=500)
    source_url: str = Field(min_length=8, max_length=2000)
    what_changed: str = Field(min_length=8, max_length=2000)
    why_it_matters: str = Field(min_length=8, max_length=2000)
    evidence_strength: str = Field(min_length=4, max_length=400)
    uncertainty_note: str = Field(min_length=4, max_length=1200)


class ConditionDigestOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=8, max_length=240)
    overview: str = Field(min_length=40, max_length=4000)
    items: list[ConditionDigestItemOut] = Field(default_factory=list, max_length=12)
    what_still_uncertain: str = Field(min_length=10, max_length=2000)
