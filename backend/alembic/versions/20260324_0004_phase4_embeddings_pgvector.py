"""phase4 embeddings pgvector table

Revision ID: 20260324_0004
Revises: 20260324_0003
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260324_0004"
down_revision: Union[str, None] = "20260324_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_item_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "research_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("embedding", sa.JSON(), nullable=False),
    )

    op.create_index("ix_research_item_embeddings_research_item_id", "research_item_embeddings", ["research_item_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_research_item_embeddings_research_item_id", table_name="research_item_embeddings")
    op.drop_table("research_item_embeddings")
