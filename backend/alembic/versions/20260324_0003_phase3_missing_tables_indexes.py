"""phase3 missing tables (trials, AI, admin jobs)

Revision ID: 20260324_0003
Revises: 20260324_0002
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260324_0003"
down_revision: Union[str, None] = "20260324_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ResearchItemAI
    op.create_table(
        "research_item_ai",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("research_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_items.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("lay_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("clinician_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("why_it_matters", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_stage", sa.String(length=64), nullable=False, server_default="basic_research"),
        sa.Column("confidence_level", sa.String(length=32), nullable=False, server_default="low"),
        sa.Column("hype_risk", sa.String(length=64), nullable=False, server_default="hypothesis_generating_only"),
        sa.Column("applicability_age_group", sa.String(length=16), nullable=False, server_default="both"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("novelty_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actionability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("structured_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("model_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("prompt_version", sa.String(length=50), nullable=False, server_default="v1"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_item_ai_evidence_stage", "research_item_ai", ["evidence_stage"], unique=False)

    # Trials
    op.create_table(
        "trials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("condition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conditions.id"), nullable=False),
        sa.Column("research_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_items.id"), nullable=True),
        sa.Column("nct_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("phase", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("intervention", sa.Text(), nullable=False, server_default=""),
        sa.Column("eligibility_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("age_max", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=32), nullable=False, server_default="all"),
        sa.Column("countries_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("locations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("primary_endpoint", sa.Text(), nullable=False, server_default=""),
        sa.Column("primary_endpoint_plain_language", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trials_condition_status_phase", "trials", ["condition_id", "status", "phase"], unique=False)
    op.create_index("ix_trials_nct_unique", "trials", ["nct_id"], unique=True)

    # Digests
    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("condition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conditions.id"), nullable=False),
        sa.Column("digest_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("structured_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_digests_user_condition", "digests", ["user_id", "condition_id"], unique=False)

    # Ask AI
    op.create_table(
        "ask_ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("condition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conditions.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ask_ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ask_ai_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("citations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ask_ai_messages_conversation_id", "ask_ai_messages", ["conversation_id"], unique=False)

    # Bookmarks
    op.create_table(
        "bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("research_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bookmarks_user_item_unique", "bookmarks", ["user_id", "research_item_id"], unique=True)

    # AdminJobRun
    op.create_table(
        "admin_job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("output_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("error_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_job_runs_job_type", "admin_job_runs", ["job_type"], unique=False)
    op.create_index("ix_admin_job_runs_status", "admin_job_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_job_runs_status", table_name="admin_job_runs")
    op.drop_index("ix_admin_job_runs_job_type", table_name="admin_job_runs")
    op.drop_table("admin_job_runs")

    op.drop_index("ix_bookmarks_user_item_unique", table_name="bookmarks")
    op.drop_table("bookmarks")

    op.drop_index("ix_ask_ai_messages_conversation_id", table_name="ask_ai_messages")
    op.drop_table("ask_ai_messages")
    op.drop_table("ask_ai_conversations")

    op.drop_index("ix_digests_user_condition", table_name="digests")
    op.drop_table("digests")

    op.drop_index("ix_trials_nct_unique", table_name="trials")
    op.drop_index("ix_trials_condition_status_phase", table_name="trials")
    op.drop_table("trials")

    op.drop_index("ix_research_item_ai_evidence_stage", table_name="research_item_ai")
    op.drop_table("research_item_ai")

