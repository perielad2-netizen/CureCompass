from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TrialListItem(BaseModel):
    id: str
    nct_id: str
    status: str
    phase: str
    title: str
    intervention: str
    eligibility_summary: str
    age_min: int | None
    age_max: int | None
    sex: str
    countries: list[Any]
    primary_endpoint_plain_language: str
    source_url: str
    last_verified_at: datetime


class TrialDetailOut(TrialListItem):
    condition_slug: str
    condition_name: str
    primary_endpoint: str
    locations: list[Any]
