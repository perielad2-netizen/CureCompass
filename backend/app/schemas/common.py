from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class APIMessage(BaseModel):
    message: str


class ConditionOut(BaseModel):
    id: UUID
    canonical_name: str
    slug: str
    description: str


class DashboardCard(BaseModel):
    id: UUID
    title: str
    source: str
    published_at: datetime
    evidence_stage: str
    why_it_matters: str
