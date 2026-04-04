from datetime import datetime

from pydantic import BaseModel


class ResearchUpdateListItem(BaseModel):
    id: str
    title: str
    source_name: str
    source_url: str
    published_at: datetime
    item_type: str
    evidence_stage: str
    evidence_stage_label: str
    summary: str
    why_it_matters: str
    confidence_level: str
    applicability_age_group: str
    bookmarked: bool = False


class ResearchUpdateDetail(ResearchUpdateListItem):
    hype_risk: str
    abstract_or_body: str


class ResearchUpdatesPage(BaseModel):
    items: list[ResearchUpdateListItem]
    total: int
