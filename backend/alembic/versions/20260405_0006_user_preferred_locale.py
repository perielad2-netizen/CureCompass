"""user preferred_locale for UI language (phase 1: en, he)

Revision ID: 20260405_0006
Revises: 20260404_0005
Create Date: 2026-04-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260405_0006"
down_revision: Union[str, None] = "20260404_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("preferred_locale", sa.String(length=10), nullable=False, server_default="en"),
    )
    op.create_index("ix_users_preferred_locale", "users", ["preferred_locale"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_preferred_locale", table_name="users")
    op.drop_column("users", "preferred_locale")
