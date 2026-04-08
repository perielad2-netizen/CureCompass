from pydantic import BaseModel, Field


class ConditionRequestIn(BaseModel):
    query: str = Field(..., min_length=2, max_length=240, strip_whitespace=True)
    locale: str = Field(default="en", pattern="^(en|he)$")


class ConditionBriefOut(BaseModel):
    id: str
    canonical_name: str
    slug: str
    description: str = ""


class ConditionRequestOut(BaseModel):
    outcome: str = Field(..., pattern="^(existing|created)$")
    condition: ConditionBriefOut
