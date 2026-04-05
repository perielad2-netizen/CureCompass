"""Expand conditions catalog (ASD, Alzheimer, Parkinson, diabetes, breast cancer, ALS) + NF1 refresh.

Revision ID: 20260409_0009
Revises: 20260408_0008
Create Date: 2026-04-09
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.conditions_catalog import CONDITIONS

revision: str = "20260409_0009"
down_revision: Union[str, None] = "20260408_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for row in CONDITIONS:
        slug = row["slug"]
        exists = conn.execute(sa.text("SELECT id FROM conditions WHERE slug = :slug"), {"slug": slug}).scalar()
        syn_json = json.dumps(row["synonyms"])
        if exists:
            conn.execute(
                sa.text(
                    """
                    UPDATE conditions
                    SET canonical_name = :cn,
                        description = :desc,
                        synonyms = CAST(:syn AS json),
                        rare_disease_flag = :rare,
                        updated_at = NOW()
                    WHERE slug = :slug
                    """
                ),
                {
                    "cn": row["canonical_name"],
                    "desc": row["description"],
                    "syn": syn_json,
                    "rare": row["rare_disease_flag"],
                    "slug": slug,
                },
            )
        else:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO conditions (
                        id, canonical_name, slug, description, synonyms, rare_disease_flag, created_at, updated_at
                    )
                    VALUES (
                        gen_random_uuid(), :cn, :slug, :desc, CAST(:syn AS json), :rare, NOW(), NOW()
                    )
                    """
                ),
                {
                    "cn": row["canonical_name"],
                    "slug": slug,
                    "desc": row["description"],
                    "syn": syn_json,
                    "rare": row["rare_disease_flag"],
                },
            )


def downgrade() -> None:
    # Non-destructive: new conditions may have user follows and research_items.
    pass
