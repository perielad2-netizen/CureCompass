import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EvidenceStage(str, enum.Enum):
    BASIC_RESEARCH = "basic_research"
    ANIMAL_PRECLINICAL = "animal_preclinical"
    EARLY_HUMAN = "early_human_study"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    RESULTS_POSTED = "results_posted"
    REGULATORY_REVIEW = "regulatory_review"
    APPROVED = "approved_guideline_impacting"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_locale: Mapped[str] = mapped_column(String(10), default="en", index=True)
    notification_defaults_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Condition(Base):
    __tablename__ = "conditions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    synonyms: Mapped[dict] = mapped_column(JSON, default=list)
    rare_disease_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class UserFollowedCondition(Base):
    __tablename__ = "user_followed_conditions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="CASCADE"), index=True)
    age_scope: Mapped[str] = mapped_column(String(24), default="both")
    geography: Mapped[str] = mapped_column(String(128), default="global")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, default=0.8)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ResearchItem(Base):
    __tablename__ = "research_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conditions.id"), index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    item_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract_or_body: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    normalized_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ResearchItemAI(Base):
    __tablename__ = "research_item_ai"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    research_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_items.id", ondelete="CASCADE"), unique=True)
    lay_summary: Mapped[str] = mapped_column(Text, default="")
    lay_summary_he: Mapped[str] = mapped_column(Text, default="")
    clinician_summary: Mapped[str] = mapped_column(Text, default="")
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    why_it_matters_he: Mapped[str] = mapped_column(Text, default="")
    evidence_stage: Mapped[EvidenceStage] = mapped_column(Enum(EvidenceStage), default=EvidenceStage.BASIC_RESEARCH, index=True)
    confidence_level: Mapped[str] = mapped_column(String(32), default="low")
    hype_risk: Mapped[str] = mapped_column(String(64), default="hypothesis_generating_only")
    applicability_age_group: Mapped[str] = mapped_column(String(16), default="both")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    actionability_score: Mapped[float] = mapped_column(Float, default=0.0)
    structured_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_name: Mapped[str] = mapped_column(String(120), default="")
    prompt_version: Mapped[str] = mapped_column(String(50), default="v1")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ResearchItemEmbedding(Base):
    __tablename__ = "research_item_embeddings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    research_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_items.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Store embeddings as JSON until pgvector is available.
    # Phase 5 will move retrieval to pgvector once the DB extension is installed.
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)


class Trial(Base):
    __tablename__ = "trials"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conditions.id"), index=True)
    research_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("research_items.id"), nullable=True)
    nct_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(64), index=True)
    phase: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    intervention: Mapped[str] = mapped_column(Text, default="")
    eligibility_summary: Mapped[str] = mapped_column(Text, default="")
    age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str] = mapped_column(String(32), default="all")
    countries_json: Mapped[dict] = mapped_column(JSON, default=list)
    locations_json: Mapped[dict] = mapped_column(JSON, default=list)
    primary_endpoint: Mapped[str] = mapped_column(Text, default="")
    primary_endpoint_plain_language: Mapped[str] = mapped_column(Text, default="")
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="CASCADE"), index=True)
    notify_trials: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_recruiting_trials_only: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_papers: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_regulatory: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_foundation_news: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_major_only: Mapped[bool] = mapped_column(Boolean, default=False)
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    quiet_hours_json: Mapped[dict] = mapped_column(JSON, default=dict)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Digest(Base):
    __tablename__ = "digests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conditions.id"), index=True)
    digest_type: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body_markdown: Mapped[str] = mapped_column(Text)
    structured_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AskAIConversation(Base):
    __tablename__ = "ask_ai_conversations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conditions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AskAIMessage(Base):
    __tablename__ = "ask_ai_messages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ask_ai_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    structured_json: Mapped[dict] = mapped_column(JSON, default=dict)
    citations_json: Mapped[dict] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserPrivateDocument(Base):
    """User-uploaded PDF (MVP) linked to a followed condition. Text stored for Ask AI context; file on disk."""

    __tablename__ = "user_private_documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    condition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_summary: Mapped[str] = mapped_column(Text, default="")
    doctor_questions_json: Mapped[list] = mapped_column(JSON, default=list)
    processing_error: Mapped[str] = mapped_column(Text, default="")
    consent_recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Bookmark(Base):
    __tablename__ = "bookmarks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    research_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_items.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ConditionIngestionCooldown(Base):
    """Last successful ingestion time per condition (shared across users)."""

    __tablename__ = "condition_ingestion_cooldown"
    condition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conditions.id", ondelete="CASCADE"), primary_key=True
    )
    last_success_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminJobRun(Base):
    __tablename__ = "admin_job_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_text: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index("ix_research_items_condition_type_date", ResearchItem.condition_id, ResearchItem.item_type, ResearchItem.published_at.desc())
Index("ix_trials_condition_status_phase", Trial.condition_id, Trial.status, Trial.phase)
Index("ix_follow_unique", UserFollowedCondition.user_id, UserFollowedCondition.condition_id, unique=True)
Index("ix_bookmark_unique", Bookmark.user_id, Bookmark.research_item_id, unique=True)
Index("ix_notification_pref_user_condition", NotificationPreference.user_id, NotificationPreference.condition_id, unique=True)
Index("ix_user_private_documents_user_condition", UserPrivateDocument.user_id, UserPrivateDocument.condition_id)
