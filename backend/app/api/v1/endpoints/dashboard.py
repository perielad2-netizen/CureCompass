from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Bookmark, Condition, Digest, ResearchItem, Trial, User, UserFollowedCondition
from app.schemas.dashboard import DashboardOut, DashboardRecruitingTrialOut, LatestUpdateOut
from app.services.research_presenter import serialize_research_item

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

CT_GOV_STUDY_URL = "https://clinicaltrials.gov/study/{nct_id}"


@router.get("", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    locale: Literal["en", "he"] = Query(default="en", description="UI locale for digest preview fallbacks"),
):
    follows = db.scalars(select(UserFollowedCondition).where(UserFollowedCondition.user_id == current_user.id)).all()
    condition_ids = [f.condition_id for f in follows]
    conditions = db.scalars(select(Condition).where(Condition.id.in_(condition_ids))).all() if condition_ids else []
    recent_items = (
        db.scalars(
            select(ResearchItem)
            .where(ResearchItem.condition_id.in_(condition_ids))
            .order_by(ResearchItem.published_at.desc())
            .limit(8)
        ).all()
        if condition_ids
        else []
    )

    bookmarked_ids: set[UUID] = set()
    if recent_items:
        ids = [i.id for i in recent_items]
        bookmarked_ids = set(
            db.scalars(
                select(Bookmark.research_item_id).where(
                    Bookmark.user_id == current_user.id,
                    Bookmark.research_item_id.in_(ids),
                )
            ).all()
        )

    latest_updates: list[LatestUpdateOut] = []
    for item in recent_items:
        core = serialize_research_item(db, item, locale=locale)
        cond = db.get(Condition, item.condition_id)
        latest_updates.append(
            LatestUpdateOut(
                id=core["id"],
                title=core["title"],
                source_url=core["source_url"],
                published_at=core["published_at"],
                item_type=core["item_type"],
                evidence_stage=core["evidence_stage"],
                evidence_stage_label=core["evidence_stage_label"],
                summary=core["summary"],
                why_it_matters=core["why_it_matters"],
                recap_locale=core["recap_locale"],
                bookmarked=item.id in bookmarked_ids,
                condition_slug=cond.slug if cond else "",
                condition_name=cond.canonical_name if cond else "",
            )
        )

    latest_digest = db.scalar(
        select(Digest)
        .where(Digest.user_id == current_user.id)
        .order_by(Digest.created_at.desc())
        .limit(1)
    )
    if latest_digest:
        digest_preview = latest_digest.title
        digest_preview_kind = "latest_digest"
    elif not recent_items:
        digest_preview_kind = "empty_feed"
        digest_preview = (
            "אין שינויים גדולים ב־24 השעות האחרונות."
            if locale == "he"
            else "No major changes in the last 24 hours."
        )
    else:
        digest_preview_kind = "has_updates"
        digest_preview = (
            "יש לכם עדכונים מהימנים חדשים."
            if locale == "he"
            else "You have new trusted updates available."
        )

    recruiting: list[DashboardRecruitingTrialOut] = []
    if condition_ids:
        cond_by_id = {c.id: c for c in conditions}
        trial_rows = db.scalars(
            select(Trial)
            .where(Trial.condition_id.in_(condition_ids))
            .where(Trial.status.ilike("%recruit%"))
            .order_by(Trial.last_verified_at.desc())
            .limit(8)
        ).all()
        for t in trial_rows:
            cond = cond_by_id.get(t.condition_id)
            recruiting.append(
                DashboardRecruitingTrialOut(
                    id=str(t.id),
                    nct_id=t.nct_id,
                    title=t.title,
                    status=t.status,
                    phase=t.phase or "",
                    condition_slug=cond.slug if cond else "",
                    condition_name=cond.canonical_name if cond else "",
                    source_url=CT_GOV_STUDY_URL.format(nct_id=t.nct_id),
                )
            )

    return {
        "followed_conditions": [{"id": str(c.id), "slug": c.slug, "name": c.canonical_name} for c in conditions],
        "latest_important_updates": latest_updates,
        "unread_updates": 0,
        "digest_preview": digest_preview,
        "digest_preview_kind": digest_preview_kind,
        "upcoming_recruiting_trials": recruiting,
    }
