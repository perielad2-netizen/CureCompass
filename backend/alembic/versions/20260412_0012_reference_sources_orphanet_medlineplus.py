"""Add Orphanet (Orphadata) and MedlinePlus (NLM) to sources catalog for admin transparency.

These match live reference providers used in medical_intel (not ingestion adapters).

Revision ID: 20260412_0012
Revises: 20260411_0011
Create Date: 2026-04-12
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260412_0012"
down_revision: Union[str, None] = "20260411_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sql_literal(s: str) -> str:
    return s.replace("'", "''")


def upgrade() -> None:
    rows = [
        ("Orphanet (Orphadata)", "reference", "https://www.orpha.net", 0.95),
        ("MedlinePlus (NLM)", "reference", "https://medlineplus.gov", 0.95),
    ]
    for name, source_type, base_url, trust in rows:
        n, st, u = _sql_literal(name), _sql_literal(source_type), _sql_literal(base_url)
        op.execute(
            text(
                f"""
                INSERT INTO sources (id, name, source_type, base_url, trust_score, enabled)
                SELECT gen_random_uuid(), '{n}', '{st}', '{u}', {float(trust)}, true
                WHERE NOT EXISTS (SELECT 1 FROM sources WHERE name = '{n}')
                """
            )
        )


def downgrade() -> None:
    op.execute(text("DELETE FROM sources WHERE name IN ('Orphanet (Orphadata)', 'MedlinePlus (NLM)')"))
