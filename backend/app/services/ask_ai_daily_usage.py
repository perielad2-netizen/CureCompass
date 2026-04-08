"""Free-tier daily Ask AI limits (UTC day). Premium users bypass via ``User.is_premium``."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AskAIDailyUsage, User

ASK_AI_SOFT_LIMIT = 5
ASK_AI_GRACE_SLOTS = 2
ASK_AI_MAX_PER_DAY = ASK_AI_SOFT_LIMIT + ASK_AI_GRACE_SLOTS

FREE_DAILY_LIMIT_MESSAGE = (
    "To keep answers accurate and based on trusted medical sources,\n\n"
    "we limit free usage.\n\n"
    "You'll get more questions tomorrow."
)


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def should_enforce_ask_ai_limit(user: User) -> bool:
    return not bool(getattr(user, "is_premium", False))


def _snapshot_from_count(count: int, *, is_premium: bool) -> dict[str, Any]:
    if is_premium:
        return {
            "count": count,
            "remaining": None,
            "soft_limit": ASK_AI_SOFT_LIMIT,
            "grace_limit": ASK_AI_GRACE_SLOTS,
            "max_limit": ASK_AI_MAX_PER_DAY,
            "is_limited": False,
            "in_grace_zone": False,
            "is_premium": True,
        }
    remaining = max(0, ASK_AI_MAX_PER_DAY - count)
    return {
        "count": count,
        "remaining": remaining,
        "soft_limit": ASK_AI_SOFT_LIMIT,
        "grace_limit": ASK_AI_GRACE_SLOTS,
        "max_limit": ASK_AI_MAX_PER_DAY,
        "is_limited": count >= ASK_AI_MAX_PER_DAY,
        "in_grace_zone": count >= ASK_AI_SOFT_LIMIT and count < ASK_AI_MAX_PER_DAY,
        "is_premium": False,
    }


def get_today_usage_row(db: Session, user_id: uuid.UUID, *, day: date | None = None) -> AskAIDailyUsage | None:
    d = day if day is not None else utc_today()
    return db.scalar(select(AskAIDailyUsage).where(AskAIDailyUsage.user_id == user_id, AskAIDailyUsage.usage_date == d))


def get_or_create_today_usage_row(db: Session, user_id: uuid.UUID, *, day: date | None = None) -> AskAIDailyUsage:
    d = day if day is not None else utc_today()
    row = get_today_usage_row(db, user_id, day=d)
    if row:
        return row
    row = AskAIDailyUsage(user_id=user_id, usage_date=d, request_count=0, blocked_count=0)
    db.add(row)
    db.flush()
    return row


def user_ask_ai_usage_snapshot(db: Session, user: User) -> dict[str, Any]:
    if should_enforce_ask_ai_limit(user):
        row = get_today_usage_row(db, user.id)
        count = int(row.request_count) if row else 0
        return _snapshot_from_count(count, is_premium=False)
    row = get_today_usage_row(db, user.id)
    count = int(row.request_count) if row else 0
    return _snapshot_from_count(count, is_premium=True)


def can_user_ask_ai(db: Session, user: User) -> bool:
    if not should_enforce_ask_ai_limit(user):
        return True
    row = get_today_usage_row(db, user.id)
    count = int(row.request_count) if row else 0
    return count < ASK_AI_MAX_PER_DAY


def record_ask_ai_block(db: Session, user_id: uuid.UUID) -> None:
    row = get_or_create_today_usage_row(db, user_id)
    row.blocked_count = int(row.blocked_count or 0) + 1
    db.flush()


def increment_successful_ask(db: Session, user_id: uuid.UUID) -> None:
    row = get_or_create_today_usage_row(db, user_id)
    now = datetime.now(timezone.utc)
    if row.first_request_at is None:
        row.first_request_at = now
    row.last_request_at = now
    row.request_count = int(row.request_count or 0) + 1
    c = row.request_count
    if c >= ASK_AI_SOFT_LIMIT and row.reached_soft_limit_at is None:
        row.reached_soft_limit_at = now
    if c >= ASK_AI_MAX_PER_DAY and row.reached_max_limit_at is None:
        row.reached_max_limit_at = now
    db.flush()


def blocked_response_payload(db: Session, user: User) -> dict[str, Any]:
    return {
        "limit_reached": True,
        "remaining": 0,
        "message": FREE_DAILY_LIMIT_MESSAGE,
        "usage": user_ask_ai_usage_snapshot(db, user),
    }


def success_usage_extras(db: Session, user: User) -> dict[str, Any]:
    return {
        "limit_reached": False,
        "usage": user_ask_ai_usage_snapshot(db, user),
    }


def median_int(values: list[int]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0
