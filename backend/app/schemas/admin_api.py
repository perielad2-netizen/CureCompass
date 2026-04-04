from datetime import datetime

from pydantic import BaseModel, Field


class AdminJobRunOut(BaseModel):
    id: str
    job_type: str
    status: str
    payload_json: dict
    output_json: dict
    error_text: str
    started_at: datetime
    finished_at: datetime | None


class AdminSourceOut(BaseModel):
    id: str
    name: str
    source_type: str
    base_url: str
    trust_score: float
    enabled: bool


class AdminSourcePatchIn(BaseModel):
    enabled: bool = Field(description="Whether this source is used during ingestion")
