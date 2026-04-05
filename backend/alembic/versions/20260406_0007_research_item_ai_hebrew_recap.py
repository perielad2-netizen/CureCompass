"""research_item_ai Hebrew recap fields

Revision ID: 20260406_0007
Revises: 20260405_0006
Create Date: 2026-04-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260406_0007"
down_revision: Union[str, None] = "20260405_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "research_item_ai",
        sa.Column("lay_summary_he", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "research_item_ai",
        sa.Column("why_it_matters_he", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("research_item_ai", "lay_summary_he", server_default=None)
    op.alter_column("research_item_ai", "why_it_matters_he", server_default=None)


def downgrade() -> None:
    op.drop_column("research_item_ai", "why_it_matters_he")
    op.drop_column("research_item_ai", "lay_summary_he")
