from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator


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
    condition_slugs: list[str] = Field(
        default_factory=list,
        description="If non-empty, only these followed conditions (by slug). If empty, all followed conditions.",
    )
    condition_slug: str | None = Field(
        default=None,
        description="Deprecated: single slug. Used only when condition_slugs is empty.",
    )

    @model_validator(mode="after")
    def _normalize_condition_slugs(self) -> Self:
        slugs = [s.strip() for s in self.condition_slugs if isinstance(s, str) and s.strip()]
        legacy = (self.condition_slug or "").strip()
        if legacy and not slugs:
            slugs = [legacy]
        return self.model_copy(update={"condition_slugs": slugs})
