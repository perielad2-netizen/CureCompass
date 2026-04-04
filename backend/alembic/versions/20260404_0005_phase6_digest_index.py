"""phase6 digest listing index

Revision ID: 20260404_0005
Revises: 20260324_0004
Create Date: 2026-04-04
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260404_0005"
down_revision: Union[str, None] = "20260324_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_digests_user_created", "digests", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_digests_user_created", table_name="digests")
