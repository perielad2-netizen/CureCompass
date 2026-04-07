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


class AdminKpiTotalsOut(BaseModel):
    users_total: int
    admins_total: int
    users_created_30d: int
    users_locale_he: int
    users_locale_en: int
    users_with_follows: int
    follows_total: int
    users_with_email_briefings_enabled: int
    users_with_in_app_briefings_enabled: int
    digests_total: int
    digests_delivered_total: int
    digest_users_total: int
    ask_ai_messages_total: int
    ask_ai_conversations_total: int
    ask_ai_users_total: int
    private_docs_total: int
    private_docs_processed: int


class AdminUsageByUserOut(BaseModel):
    user_id: str
    email: str
    preferred_locale: str
    created_at: datetime
    followed_conditions: int
    ask_ai_messages: int
    ask_ai_conversations: int
    digests_created: int
    digests_delivered: int
    has_email_briefings_enabled: bool
    has_in_app_briefings_enabled: bool
    last_ai_message_at: datetime | None
    last_digest_at: datetime | None


class AdminReportsOut(BaseModel):
    generated_at: datetime
    totals: AdminKpiTotalsOut
    top_ai_users: list[AdminUsageByUserOut]
    recent_users: list[AdminUsageByUserOut]
