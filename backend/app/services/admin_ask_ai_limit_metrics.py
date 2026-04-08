"""Aggregate Ask AI daily-limit metrics for admin (privacy-safe counts only)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import AskAIDailyUsage
from app.schemas.admin_api import AdminAskAiLimitAnalyticsOut, AdminAskAiLimitDailyRowOut
from app.services.ask_ai_daily_usage import ASK_AI_MAX_PER_DAY, ASK_AI_SOFT_LIMIT, median_int


def _daterange(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def compute_ask_ai_limit_analytics(db: Session, *, period_start: date, period_end: date) -> AdminAskAiLimitAnalyticsOut:
    """Load usage rows overlapping [period_start - 1d, period_end + 1d] for next-day return."""
    load_start = period_start - timedelta(days=1)
    load_end = period_end + timedelta(days=1)

    rows = db.scalars(
        select(AskAIDailyUsage).where(
            AskAIDailyUsage.usage_date >= load_start,
            AskAIDailyUsage.usage_date <= load_end,
        )
    ).all()

    by_pair: dict[tuple[uuid.UUID, date], AskAIDailyUsage] = {(r.user_id, r.usage_date): r for r in rows}

    period_rows = [r for r in rows if period_start <= r.usage_date <= period_end]

    users_with_usage = {r.user_id for r in period_rows if int(r.request_count or 0) > 0}
    n_users = len(users_with_usage)

    hit_soft_users = {r.user_id for r in period_rows if int(r.request_count or 0) >= ASK_AI_SOFT_LIMIT}
    hit_max_users = {r.user_id for r in period_rows if int(r.request_count or 0) >= ASK_AI_MAX_PER_DAY}

    n_hit_soft = len(hit_soft_users & users_with_usage)
    n_hit_max = len(hit_max_users & users_with_usage)

    pct_soft = (100.0 * n_hit_soft / n_users) if n_users else None
    pct_max = (100.0 * n_hit_max / n_users) if n_users else None

    per_row_counts = [int(r.request_count) for r in period_rows if int(r.request_count or 0) > 0]
    avg_per_user_day = sum(per_row_counts) / len(per_row_counts) if per_row_counts else None
    med_per_user_day = median_int(per_row_counts)

    soft_deltas: list[float] = []
    max_deltas: list[float] = []
    for r in period_rows:
        if int(r.request_count or 0) >= ASK_AI_SOFT_LIMIT and r.first_request_at and r.reached_soft_limit_at:
            soft_deltas.append((r.reached_soft_limit_at - r.first_request_at).total_seconds())
        if int(r.request_count or 0) >= ASK_AI_MAX_PER_DAY and r.first_request_at and r.reached_max_limit_at:
            max_deltas.append((r.reached_max_limit_at - r.first_request_at).total_seconds())

    avg_to_soft = sum(soft_deltas) / len(soft_deltas) if soft_deltas else None
    avg_to_max = sum(max_deltas) / len(max_deltas) if max_deltas else None

    # Next-day return: (user, D) where hit soft on D and any request_count>0 on D+1
    def next_day_return_rate(hit_at_least: int) -> float | None:
        events: list[tuple[uuid.UUID, date]] = []
        for r in period_rows:
            if int(r.request_count or 0) >= hit_at_least and period_start <= r.usage_date <= period_end:
                events.append((r.user_id, r.usage_date))
        if not events:
            return None
        returned = 0
        for uid, d in events:
            nxt = d + timedelta(days=1)
            nxt_row = by_pair.get((uid, nxt))
            if nxt_row and int(nxt_row.request_count or 0) > 0:
                returned += 1
        return 100.0 * returned / len(events)

    next_soft = next_day_return_rate(ASK_AI_SOFT_LIMIT)
    next_max = next_day_return_rate(ASK_AI_MAX_PER_DAY)

    daily_rows: list[AdminAskAiLimitDailyRowOut] = []
    for d in _daterange(period_start, period_end):
        day_rows = [r for r in period_rows if r.usage_date == d]
        ask_users = len({r.user_id for r in day_rows if int(r.request_count or 0) > 0})
        u_hit5 = {r.user_id for r in day_rows if int(r.request_count or 0) >= ASK_AI_SOFT_LIMIT}
        u_hit7 = {r.user_id for r in day_rows if int(r.request_count or 0) >= ASK_AI_MAX_PER_DAY}
        hit5 = len(u_hit5)
        hit7 = len(u_hit7)
        total_req = sum(int(r.request_count or 0) for r in day_rows)
        avg_req = (total_req / ask_users) if ask_users else 0.0

        def day_next_rate(hit_set: set[uuid.UUID]) -> float | None:
            if not hit_set:
                return None
            ok = 0
            for uid in hit_set:
                nxt_row = by_pair.get((uid, d + timedelta(days=1)))
                if nxt_row and int(nxt_row.request_count or 0) > 0:
                    ok += 1
            return 100.0 * ok / len(hit_set)

        daily_rows.append(
            AdminAskAiLimitDailyRowOut(
                usage_date=d.isoformat(),
                ask_users=ask_users,
                users_hit_soft=hit5,
                users_hit_max=hit7,
                avg_requests_per_user=round(avg_req, 3),
                next_day_return_hit_soft_pct=day_next_rate(u_hit5),
                next_day_return_hit_max_pct=day_next_rate(u_hit7),
            )
        )

    blocked_total = int(
        db.scalar(
            select(func.coalesce(func.sum(AskAIDailyUsage.blocked_count), 0)).where(
                AskAIDailyUsage.usage_date >= period_start,
                AskAIDailyUsage.usage_date <= period_end,
            )
        )
        or 0
    )

    return AdminAskAiLimitAnalyticsOut(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        ask_users_with_usage=n_users,
        users_ever_hit_soft=n_hit_soft,
        users_ever_hit_max=n_hit_max,
        pct_ask_users_hit_soft=round(pct_soft, 2) if pct_soft is not None else None,
        pct_ask_users_hit_max=round(pct_max, 2) if pct_max is not None else None,
        avg_requests_per_user_day=round(avg_per_user_day, 3) if avg_per_user_day is not None else None,
        median_requests_per_user_day=med_per_user_day,
        avg_seconds_first_to_soft=round(avg_to_soft, 1) if avg_to_soft is not None else None,
        avg_seconds_first_to_max=round(avg_to_max, 1) if avg_to_max is not None else None,
        next_day_return_after_hit_soft_pct=round(next_soft, 2) if next_soft is not None else None,
        next_day_return_after_hit_max_pct=round(next_max, 2) if next_max is not None else None,
        blocked_attempts_total=blocked_total,
        daily_rows=daily_rows,
    )
