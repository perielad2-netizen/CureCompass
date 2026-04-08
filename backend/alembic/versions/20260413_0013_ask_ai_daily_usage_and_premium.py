"""Ask AI daily usage limits + is_premium placeholder on users.

Revision ID: 20260413_0013
Revises: 20260412_0012
Create Date: 2026-04-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260413_0013"
down_revision: Union[str, None] = "20260412_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.alter_column("users", "is_premium", server_default=None)

    op.create_table(
        "ask_ai_daily_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reached_soft_limit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reached_max_limit_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_ask_ai_daily_usage_user_date"),
    )
    op.create_index("ix_ask_ai_daily_usage_usage_date", "ask_ai_daily_usage", ["usage_date"])


def downgrade() -> None:
    op.drop_index("ix_ask_ai_daily_usage_usage_date", table_name="ask_ai_daily_usage")
    op.drop_table("ask_ai_daily_usage")
    op.drop_column("users", "is_premium")
