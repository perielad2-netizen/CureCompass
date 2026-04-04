"""phase2 password reset, notification preferences, user defaults

Revision ID: 20260324_0002
Revises: 20260323_0001
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260324_0002"
down_revision: Union[str, None] = "20260323_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notification_defaults_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("condition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conditions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notify_trials", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_recruiting_trials_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notify_papers", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_regulatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_foundation_news", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_major_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="daily"),
        sa.Column("quiet_hours_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_notification_pref_user_condition", "notification_preferences", ["user_id", "condition_id"], unique=True)
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_index("ix_notification_pref_user_condition", table_name="notification_preferences")
    op.drop_table("notification_preferences")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "notification_defaults_json")
