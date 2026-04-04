from datetime import datetime

from pydantic import BaseModel


class BookmarkToggleOut(BaseModel):
    research_item_id: str
    bookmarked: bool
    created_at: str | None = None


class BookmarkListItem(BaseModel):
    research_item_id: str
    created_at: datetime
    condition_slug: str
    title: str
    source_name: str
    source_url: str
    evidence_stage_label: str
    summary: str
