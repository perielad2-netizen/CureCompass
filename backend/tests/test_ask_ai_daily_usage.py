"""Ask AI daily usage limits (UTC day)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import entities as _entities  # noqa: F401 — register mappers
from app.models.base import Base
from app.models.entities import AskAIDailyUsage, User
from app.services.ask_ai_daily_usage import (
    ASK_AI_MAX_PER_DAY,
    ASK_AI_SOFT_LIMIT,
    can_user_ask_ai,
    get_today_usage_row,
    increment_successful_ask,
    record_ask_ai_block,
    should_enforce_ask_ai_limit,
    user_ask_ai_usage_snapshot,
)
from app.services.admin_ask_ai_limit_metrics import compute_ask_ai_limit_analytics


@pytest.fixture()
def sqlite_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        uid = uuid.uuid4()
        db.add(
            User(
                id=uid,
                email="t@example.com",
                hashed_password="x",
                is_admin=False,
                is_premium=False,
            )
        )
        db.commit()
        db.info["test_user_id"] = uid
        yield db
    finally:
        db.close()


def _user(db: Session) -> User:
    uid = db.info["test_user_id"]
    return db.get(User, uid)


def test_new_user_zero_usage(sqlite_session):
    u = _user(sqlite_session)
    snap = user_ask_ai_usage_snapshot(sqlite_session, u)
    assert snap["count"] == 0
    assert snap["remaining"] == ASK_AI_MAX_PER_DAY
    assert snap["is_limited"] is False
    assert can_user_ask_ai(sqlite_session, u) is True


def test_questions_one_through_seven_allowed_eighth_blocked(sqlite_session):
    u = _user(sqlite_session)
    for i in range(ASK_AI_MAX_PER_DAY):
        assert can_user_ask_ai(sqlite_session, u) is True
        increment_successful_ask(sqlite_session, u.id)
        sqlite_session.commit()
    assert can_user_ask_ai(sqlite_session, u) is False
    snap = user_ask_ai_usage_snapshot(sqlite_session, u)
    assert snap["count"] == ASK_AI_MAX_PER_DAY
    assert snap["remaining"] == 0
    assert snap["is_limited"] is True


def test_grace_zone_flag(sqlite_session):
    u = _user(sqlite_session)
    for _ in range(ASK_AI_SOFT_LIMIT - 1):
        increment_successful_ask(sqlite_session, u.id)
    sqlite_session.commit()
    snap = user_ask_ai_usage_snapshot(sqlite_session, u)
    assert snap["in_grace_zone"] is False
    increment_successful_ask(sqlite_session, u.id)
    sqlite_session.commit()
    snap = user_ask_ai_usage_snapshot(sqlite_session, u)
    assert snap["count"] == ASK_AI_SOFT_LIMIT
    assert snap["in_grace_zone"] is True


def test_record_block_increments_blocked_count(sqlite_session):
    u = _user(sqlite_session)
    record_ask_ai_block(sqlite_session, u.id)
    sqlite_session.commit()
    row = get_today_usage_row(sqlite_session, u.id)
    assert row is not None
    assert row.blocked_count == 1
    assert row.request_count == 0


def test_premium_bypass(sqlite_session):
    u = _user(sqlite_session)
    u.is_premium = True
    sqlite_session.commit()
    for _ in range(ASK_AI_MAX_PER_DAY + 3):
        increment_successful_ask(sqlite_session, u.id)
    sqlite_session.commit()
    assert should_enforce_ask_ai_limit(u) is False
    assert can_user_ask_ai(sqlite_session, u) is True
    snap = user_ask_ai_usage_snapshot(sqlite_session, u)
    assert snap["is_premium"] is True
    assert snap["is_limited"] is False
    assert snap["remaining"] is None


def test_next_day_reset(sqlite_session):
    u = _user(sqlite_session)
    yesterday = date(2030, 1, 15)
    row = AskAIDailyUsage(user_id=u.id, usage_date=yesterday, request_count=ASK_AI_MAX_PER_DAY)
    sqlite_session.add(row)
    sqlite_session.commit()

    def fake_today():
        return date(2030, 1, 16)

    from app.services import ask_ai_daily_usage as m

    orig = m.utc_today
    m.utc_today = fake_today
    try:
        snap = user_ask_ai_usage_snapshot(sqlite_session, u)
        assert snap["count"] == 0
        assert can_user_ask_ai(sqlite_session, u) is True
    finally:
        m.utc_today = orig


def test_admin_metrics_empty(sqlite_session):
    start = date(2031, 6, 1)
    end = date(2031, 6, 3)
    out = compute_ask_ai_limit_analytics(sqlite_session, period_start=start, period_end=end)
    assert out.ask_users_with_usage == 0
    assert out.blocked_attempts_total == 0
    assert len(out.daily_rows) == 3
    assert out.pct_ask_users_hit_soft is None


def test_admin_hit_soft_and_percentages(sqlite_session):
    u = _user(sqlite_session)
    d = date(2032, 3, 10)
    row = AskAIDailyUsage(
        user_id=u.id,
        usage_date=d,
        request_count=ASK_AI_SOFT_LIMIT,
        blocked_count=0,
        first_request_at=datetime(2032, 3, 10, 8, 0, tzinfo=timezone.utc),
        reached_soft_limit_at=datetime(2032, 3, 10, 9, 0, tzinfo=timezone.utc),
    )
    sqlite_session.add(row)
    sqlite_session.commit()

    out = compute_ask_ai_limit_analytics(sqlite_session, period_start=d, period_end=d)
    assert out.ask_users_with_usage == 1
    assert out.users_ever_hit_soft == 1
    assert out.users_ever_hit_max == 0
    assert out.pct_ask_users_hit_soft == 100.0
    assert out.pct_ask_users_hit_max in (0.0, None)
    day = out.daily_rows[0]
    assert day.users_hit_soft == 1


def test_admin_next_day_return(sqlite_session):
    u = _user(sqlite_session)
    d0 = date(2033, 1, 5)
    d1 = date(2033, 1, 6)
    sqlite_session.add(
        AskAIDailyUsage(
            user_id=u.id,
            usage_date=d0,
            request_count=ASK_AI_SOFT_LIMIT,
            first_request_at=datetime(2033, 1, 5, 1, 0, tzinfo=timezone.utc),
            reached_soft_limit_at=datetime(2033, 1, 5, 2, 0, tzinfo=timezone.utc),
        )
    )
    sqlite_session.add(AskAIDailyUsage(user_id=u.id, usage_date=d1, request_count=1))
    sqlite_session.commit()

    out = compute_ask_ai_limit_analytics(sqlite_session, period_start=d0, period_end=d0)
    assert out.next_day_return_after_hit_soft_pct == 100.0


def test_median_helper():
    from app.services.ask_ai_daily_usage import median_int

    assert median_int([1, 2, 3, 4]) == 2.5
    assert median_int([5]) == 5.0
    assert median_int([]) is None
