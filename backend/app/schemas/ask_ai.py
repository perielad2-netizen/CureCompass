from pydantic import BaseModel, Field


class AskAIIn(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    conversation_id: str | None = None


class AskAISource(BaseModel):
    research_item_id: str
    title: str
    source_url: str
    published_at: str
    item_type: str


class AskAIAnswerOut(BaseModel):
    direct_answer: str
    what_changed_recently: str
    evidence_strength: str
    available_now_or_experimental: str
    suggested_doctor_questions: list[str]
    sources: list[AskAISource]

