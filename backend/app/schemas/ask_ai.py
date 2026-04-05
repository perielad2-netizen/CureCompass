from typing import Literal

from pydantic import BaseModel, Field


class AskAIIn(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    conversation_id: str | None = None
    answer_locale: Literal["en", "he"] | None = Field(
        default=None,
        description="If set, overrides the signed-in user's saved UI language for this answer only.",
    )
    mode: Literal["research_only", "documents_only", "research_and_documents"] = Field(
        default="research_only",
        description="Which evidence pools may be used: indexed research, your uploaded PDFs for this condition, or both.",
    )
    document_ids: list[str] = Field(
        default_factory=list,
        description="When using private documents, optionally restrict to these document UUIDs (must belong to you and this condition).",
    )


class AskAISource(BaseModel):
    research_item_id: str = Field(default="", max_length=80)
    document_id: str = Field(default="", max_length=80)
    title: str
    source_url: str = Field(default="", max_length=4000)
    published_at: str = Field(default="", max_length=80)
    item_type: str = Field(default="", max_length=80)


class AskAIAnswerOut(BaseModel):
    direct_answer: str
    what_changed_recently: str
    evidence_strength: str
    available_now_or_experimental: str
    suggested_doctor_questions: list[str]
    sources: list[AskAISource]

