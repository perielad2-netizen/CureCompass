"""user private documents (PDF MVP)

Revision ID: 20260408_0008
Revises: 20260406_0007
Create Date: 2026-04-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260408_0008"
down_revision: Union[str, None] = "20260406_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_private_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("condition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("stored_filename", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("processing_status", sa.String(length=24), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("patient_summary", sa.Text(), nullable=False),
        sa.Column("doctor_questions_json", sa.JSON(), nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=False),
        sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["condition_id"], ["conditions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_private_documents_user_id", "user_private_documents", ["user_id"], unique=False)
    op.create_index("ix_user_private_documents_condition_id", "user_private_documents", ["condition_id"], unique=False)
    op.create_index("ix_user_private_documents_processing_status", "user_private_documents", ["processing_status"], unique=False)
    op.create_index(
        "ix_user_private_documents_user_condition",
        "user_private_documents",
        ["user_id", "condition_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_private_documents_user_condition", table_name="user_private_documents")
    op.drop_index("ix_user_private_documents_processing_status", table_name="user_private_documents")
    op.drop_index("ix_user_private_documents_condition_id", table_name="user_private_documents")
    op.drop_index("ix_user_private_documents_user_id", table_name="user_private_documents")
    op.drop_table("user_private_documents")
