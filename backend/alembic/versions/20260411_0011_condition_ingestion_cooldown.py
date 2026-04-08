"""condition_ingestion_cooldown: last successful ingestion per condition (4h dedup for users).

Revision ID: 20260411_0011
Revises: 20260410_0010
Create Date: 2026-04-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260411_0011"
down_revision: Union[str, None] = "20260410_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "condition_ingestion_cooldown",
        sa.Column("condition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["condition_id"], ["conditions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("condition_id"),
    )


def downgrade() -> None:
    op.drop_table("condition_ingestion_cooldown")
