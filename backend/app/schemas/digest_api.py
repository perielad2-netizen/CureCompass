from datetime import datetime

from pydantic import BaseModel, Field


class DigestSummaryOut(BaseModel):
    id: str
    digest_type: str
    title: str
    condition_slug: str
    condition_name: str
    created_at: datetime
    email_delivered: bool


class DigestDetailOut(DigestSummaryOut):
    body_markdown: str
    structured_json: dict


class DigestGenerateIn(BaseModel):
    digest_type: str = Field(pattern="^(daily|weekly|major)$")
    condition_slug: str | None = Field(
        default=None,
        description="Limit to one followed condition; omit to run for all followed conditions.",
    )
