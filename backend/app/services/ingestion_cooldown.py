"""Shared ingestion cooldown: avoid re-fetching external APIs for the same condition too often."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import ConditionIngestionCooldown


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def cooldown_delta() -> timedelta:
    return timedelta(hours=max(1, settings.ingestion_cooldown_hours))


def get_last_success_at(db: Session, condition_id: uuid.UUID) -> datetime | None:
    row = db.get(ConditionIngestionCooldown, condition_id)
    return row.last_success_at if row else None


def should_skip_ingestion_for_user(
    db: Session,
    condition_id: uuid.UUID,
    *,
    is_admin: bool,
) -> tuple[bool, datetime | None]:
    """Non-admins skip if a successful run completed within the cooldown window."""
    if is_admin:
        return False, None
    last = get_last_success_at(db, condition_id)
    if last is None:
        return False, None
    if _utc_now() - last < cooldown_delta():
        return True, last
    return False, None


def touch_ingestion_success(db: Session, condition_id: uuid.UUID) -> None:
    """Call after a completed ingestion run (Celery task)."""
    now = _utc_now()
    row = db.get(ConditionIngestionCooldown, condition_id)
    if row:
        row.last_success_at = now
    else:
        db.add(ConditionIngestionCooldown(condition_id=condition_id, last_success_at=now))
