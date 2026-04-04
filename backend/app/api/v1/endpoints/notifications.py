from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Condition, NotificationPreference, User, UserFollowedCondition
from app.schemas.notifications import NotificationPreferencePayload

router = APIRouter(prefix="/notification-settings", tags=["notifications"])

_DEFAULT_KEYS = (
    "notify_trials",
    "notify_recruiting_trials_only",
    "notify_papers",
    "notify_regulatory",
    "notify_foundation_news",
    "notify_major_only",
    "frequency",
    "quiet_hours_json",
    "email_enabled",
    "push_enabled",
    "in_app_enabled",
)

_BUILTIN_DEFAULTS: dict = {
    "notify_trials": True,
    "notify_recruiting_trials_only": False,
    "notify_papers": True,
    "notify_regulatory": True,
    "notify_foundation_news": True,
    "notify_major_only": False,
    "frequency": "daily",
    "quiet_hours_json": {},
    "email_enabled": True,
    "push_enabled": False,
    "in_app_enabled": True,
}


def _merged_defaults(user: User) -> dict:
    stored = user.notification_defaults_json or {}
    out = {**_BUILTIN_DEFAULTS, **stored}
    return {k: out[k] for k in _DEFAULT_KEYS}


@router.get("")
def get_notification_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prefs = db.scalars(
        select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    ).all()
    condition_ids = [p.condition_id for p in prefs]
    conditions = (
        db.scalars(select(Condition).where(Condition.id.in_(condition_ids))).all() if condition_ids else []
    )
    by_id = {c.id: c for c in conditions}
    per = []
    for p in prefs:
        c = by_id.get(p.condition_id)
        per.append(
            {
                "condition_id": str(p.condition_id),
                "slug": c.slug if c else "",
                "canonical_name": c.canonical_name if c else "",
                "notify_trials": p.notify_trials,
                "notify_recruiting_trials_only": p.notify_recruiting_trials_only,
                "notify_papers": p.notify_papers,
                "notify_regulatory": p.notify_regulatory,
                "notify_foundation_news": p.notify_foundation_news,
                "notify_major_only": p.notify_major_only,
                "frequency": p.frequency,
                "quiet_hours_json": p.quiet_hours_json,
                "email_enabled": p.email_enabled,
                "push_enabled": p.push_enabled,
                "in_app_enabled": p.in_app_enabled,
            }
        )
    return {"defaults": _merged_defaults(current_user), "per_condition": per}


def _upsert_notification_pref(db: Session, user_id, condition_id, fields: dict) -> None:
    row = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.condition_id == condition_id,
        )
    )
    if row:
        for key, val in fields.items():
            setattr(row, key, val)
    else:
        db.add(NotificationPreference(user_id=user_id, condition_id=condition_id, **fields))


@router.put("")
def put_notification_settings(
    payload: NotificationPreferencePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw = payload.model_dump()
    apply_all = raw.pop("apply_to_followed_conditions", False)
    defaults_payload = {k: raw[k] for k in _DEFAULT_KEYS}
    current_user.notification_defaults_json = defaults_payload

    if apply_all:
        follows = db.scalars(
            select(UserFollowedCondition).where(UserFollowedCondition.user_id == current_user.id)
        ).all()
        for follow in follows:
            _upsert_notification_pref(db, current_user.id, follow.condition_id, defaults_payload)

    db.commit()
    return {"defaults": _merged_defaults(current_user)}
