"""Turn off research-briefing email for a user (all conditions + defaults)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import NotificationPreference, User

_PREF_KEYS = (
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


def disable_digest_email_for_user(db: Session, user_id: UUID) -> None:
    """Set email_enabled=False on every notification preference row and in user defaults."""
    prefs = db.scalars(select(NotificationPreference).where(NotificationPreference.user_id == user_id)).all()
    for p in prefs:
        p.email_enabled = False

    user = db.get(User, user_id)
    if user:
        stored = user.notification_defaults_json or {}
        merged = {**_BUILTIN_DEFAULTS, **stored, "email_enabled": False}
        user.notification_defaults_json = {k: merged[k] for k in _PREF_KEYS}
