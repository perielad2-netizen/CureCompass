from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LatestUpdateOut(BaseModel):
    id: str
    title: str
    source_url: str
    published_at: datetime
    item_type: str
    evidence_stage: str
    evidence_stage_label: str
    summary: str
    why_it_matters: str
    recap_locale: Literal["en", "he"] = "en"
    bookmarked: bool = False
    condition_slug: str = ""
    condition_name: str = ""


class DashboardRecruitingTrialOut(BaseModel):
    id: str
    nct_id: str
    title: str
    status: str
    phase: str
    condition_slug: str
    condition_name: str
    source_url: str


DigestPreviewKind = Literal["latest_digest", "empty_feed", "has_updates"]


class DashboardOut(BaseModel):
    followed_conditions: list[dict]
    latest_important_updates: list[LatestUpdateOut]
    unread_updates: int
    digest_preview: str
    digest_preview_kind: DigestPreviewKind
    upcoming_recruiting_trials: list[DashboardRecruitingTrialOut]
