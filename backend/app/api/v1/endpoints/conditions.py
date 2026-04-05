from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Text, cast, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.entities import Condition, NotificationPreference, User, UserFollowedCondition
from app.schemas.conditions import FollowConditionIn
from app.schemas.notifications import NotificationPreferencePayload

router = APIRouter(prefix="/conditions", tags=["conditions"])


def _notification_fields_from_follow(payload: FollowConditionIn) -> dict:
    return {
        "notify_trials": payload.notify_trials,
        "notify_recruiting_trials_only": payload.notify_recruiting_trials_only,
        "notify_papers": payload.notify_papers,
        "notify_regulatory": payload.notify_regulatory,
        "notify_foundation_news": payload.notify_foundation_news,
        "notify_major_only": payload.notify_major_only,
        "frequency": payload.frequency,
        "quiet_hours_json": payload.quiet_hours_json,
        "email_enabled": payload.email_enabled,
        "push_enabled": payload.push_enabled,
        "in_app_enabled": payload.in_app_enabled,
    }


def _notification_fields_from_payload(payload: NotificationPreferencePayload) -> dict:
    data = payload.model_dump()
    data.pop("apply_to_followed_conditions", None)
    return data


def _upsert_notification_pref(db: Session, user_id: UUID, condition_id: UUID, fields: dict) -> None:
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


@router.get("")
def list_conditions(db: Session = Depends(get_db)):
    conditions = db.scalars(select(Condition).order_by(Condition.canonical_name.asc())).all()
    return [{"id": str(c.id), "canonical_name": c.canonical_name, "slug": c.slug, "description": c.description} for c in conditions]


@router.get("/search")
def search_conditions(q: str, db: Session = Depends(get_db)):
    """Match canonical name, URL slug, description, or any synonym (JSON list)."""
    raw = (q or "").strip()
    if not raw:
        return []
    escaped = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    syn_blob = cast(Condition.synonyms, Text)
    stmt = (
        select(Condition)
        .where(
            or_(
                Condition.canonical_name.ilike(pattern, escape="\\"),
                Condition.slug.ilike(pattern, escape="\\"),
                Condition.description.ilike(pattern, escape="\\"),
                syn_blob.ilike(pattern, escape="\\"),
            )
        )
        .order_by(Condition.canonical_name.asc())
        .limit(50)
    )
    conditions = db.scalars(stmt).all()
    return [{"id": str(c.id), "canonical_name": c.canonical_name, "slug": c.slug} for c in conditions]


@router.get("/by-slug/{slug}")
def get_condition_by_slug(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")
    followed = False
    follow_meta = None
    if current_user:
        row = db.scalar(
            select(UserFollowedCondition).where(
                UserFollowedCondition.user_id == current_user.id,
                UserFollowedCondition.condition_id == condition.id,
            )
        )
        followed = row is not None
        if row:
            follow_meta = {"age_scope": row.age_scope, "geography": row.geography}
    return {
        "id": str(condition.id),
        "canonical_name": condition.canonical_name,
        "slug": condition.slug,
        "description": condition.description,
        "synonyms": condition.synonyms,
        "rare_disease_flag": condition.rare_disease_flag,
        "followed": followed,
        "follow": follow_meta,
    }


@router.put("/by-slug/{slug}/notification-settings")
def put_condition_notification_settings(
    slug: str,
    payload: NotificationPreferencePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")
    follow = db.scalar(
        select(UserFollowedCondition).where(
            UserFollowedCondition.user_id == current_user.id,
            UserFollowedCondition.condition_id == condition.id,
        )
    )
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Follow this condition before setting notification preferences",
        )
    _upsert_notification_pref(
        db, current_user.id, condition.id, _notification_fields_from_payload(payload)
    )
    db.commit()
    return {"message": "Notification preferences updated", "condition_id": str(condition.id)}


@router.post("/{condition_id}/follow")
def follow_condition(
    condition_id: str,
    payload: FollowConditionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_condition_id = UUID(condition_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid condition id") from exc

    condition = db.get(Condition, parsed_condition_id)
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    existing = db.scalar(
        select(UserFollowedCondition).where(
            UserFollowedCondition.user_id == current_user.id,
            UserFollowedCondition.condition_id == condition.id,
        )
    )
    nfields = _notification_fields_from_follow(payload)
    if existing:
        existing.age_scope = payload.age_scope
        existing.geography = payload.geography
        _upsert_notification_pref(db, current_user.id, condition.id, nfields)
        db.commit()
        return {"message": "Follow updated", "condition_id": str(condition.id)}

    follow = UserFollowedCondition(
        user_id=current_user.id,
        condition_id=condition.id,
        age_scope=payload.age_scope,
        geography=payload.geography,
    )
    db.add(follow)
    _upsert_notification_pref(db, current_user.id, condition.id, nfields)
    db.commit()
    return {"message": "Followed condition", "condition_id": str(condition.id)}


@router.delete("/{condition_id}/follow")
def unfollow_condition(
    condition_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_condition_id = UUID(condition_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid condition id") from exc

    follow = db.scalar(
        select(UserFollowedCondition).where(
            UserFollowedCondition.user_id == current_user.id,
            UserFollowedCondition.condition_id == parsed_condition_id,
        )
    )
    if not follow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow entry not found")

    pref = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id,
            NotificationPreference.condition_id == parsed_condition_id,
        )
    )
    if pref:
        db.delete(pref)
    db.delete(follow)
    db.commit()
    return {"message": "Unfollowed condition", "condition_id": str(parsed_condition_id)}
