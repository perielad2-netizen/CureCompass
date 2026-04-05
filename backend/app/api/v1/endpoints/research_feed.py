from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.db.session import get_db
from app.models.entities import Bookmark, Condition, ResearchItem, Source, Trial, User
from app.schemas.trials_api import TrialDetailOut, TrialListItem
from app.schemas.updates import ResearchUpdateDetail, ResearchUpdateListItem, ResearchUpdatesPage
from app.services.research_presenter import serialize_research_item

router = APIRouter(tags=["research-feed"])

CT_GOV_STUDY_URL = "https://clinicaltrials.gov/study/{nct_id}"


def _trial_to_list_item(t: Trial) -> TrialListItem:
    countries = t.countries_json if isinstance(t.countries_json, list) else []
    return TrialListItem(
        id=str(t.id),
        nct_id=t.nct_id,
        status=t.status,
        phase=t.phase or "",
        title=t.title,
        intervention=t.intervention or "",
        eligibility_summary=t.eligibility_summary or "",
        age_min=t.age_min,
        age_max=t.age_max,
        sex=t.sex or "all",
        countries=countries,
        primary_endpoint_plain_language=t.primary_endpoint_plain_language or "",
        source_url=CT_GOV_STUDY_URL.format(nct_id=t.nct_id),
        last_verified_at=t.last_verified_at,
    )


def _locations_as_list(raw: object) -> list:
    if isinstance(raw, list):
        return raw
    if raw:
        return [raw]
    return []


@router.get("/conditions/by-slug/{slug}/updates", response_model=ResearchUpdatesPage)
def list_condition_updates(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    item_type: str | None = Query(None, description="Filter by item_type e.g. paper, trial, regulatory"),
    locale: Literal["en", "he"] = Query(default="en", description="UI locale for Hebrew recaps when stored"),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    count_stmt = select(func.count()).select_from(ResearchItem).where(ResearchItem.condition_id == condition.id)
    list_stmt = select(ResearchItem).where(ResearchItem.condition_id == condition.id)
    if item_type:
        count_stmt = count_stmt.where(ResearchItem.item_type == item_type)
        list_stmt = list_stmt.where(ResearchItem.item_type == item_type)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(list_stmt.order_by(ResearchItem.published_at.desc()).offset(offset).limit(limit)).all()

    bookmarked_ids: set[UUID] = set()
    if current_user:
        ids = [i.id for i in items]
        if ids:
            rows = db.scalars(
                select(Bookmark.research_item_id).where(
                    Bookmark.user_id == current_user.id,
                    Bookmark.research_item_id.in_(ids),
                )
            ).all()
            bookmarked_ids = set(rows)

    out: list[ResearchUpdateListItem] = []
    for item in items:
        src = db.get(Source, item.source_id)
        core = serialize_research_item(db, item, locale=locale)
        out.append(
            ResearchUpdateListItem(
                source_name=src.name if src else "Source",
                bookmarked=item.id in bookmarked_ids,
                **{k: v for k, v in core.items() if k in ResearchUpdateListItem.model_fields},
            )
        )

    return ResearchUpdatesPage(items=out, total=total)


@router.get("/updates/{item_id}", response_model=ResearchUpdateDetail)
def get_update_detail(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    locale: Literal["en", "he"] = Query(default="en"),
):
    try:
        parsed = UUID(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid update id") from exc

    item = db.get(ResearchItem, parsed)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update not found")

    src = db.get(Source, item.source_id)
    core = serialize_research_item(db, item, locale=locale)
    bookmarked = False
    if current_user:
        bookmarked = (
            db.scalar(
                select(Bookmark).where(
                    Bookmark.user_id == current_user.id,
                    Bookmark.research_item_id == item.id,
                )
            )
            is not None
        )

    body = item.abstract_or_body or ""
    if len(body) > 12000:
        body = body[:12000] + "\n\n…"

    return ResearchUpdateDetail(
        source_name=src.name if src else "Source",
        bookmarked=bookmarked,
        hype_risk=core["hype_risk"],
        abstract_or_body=body,
        **{k: v for k, v in core.items() if k in ResearchUpdateListItem.model_fields},
    )


@router.get("/conditions/by-slug/{slug}/trials", response_model=list[TrialListItem])
def list_condition_trials(
    slug: str,
    db: Session = Depends(get_db),
    recruiting_only: bool = False,
    phase: str | None = Query(None, description="Substring match on phase, e.g. 2"),
    limit: int = Query(50, ge=1, le=100),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    q = select(Trial).where(Trial.condition_id == condition.id)
    if recruiting_only:
        q = q.where(Trial.status.ilike("%recruit%"))
    if phase:
        q = q.where(Trial.phase.ilike(f"%{phase}%"))

    rows = db.scalars(q.order_by(Trial.last_verified_at.desc()).limit(limit)).all()
    return [_trial_to_list_item(t) for t in rows]


@router.get("/trials/{trial_id}", response_model=TrialDetailOut)
def get_trial_detail(trial_id: str, db: Session = Depends(get_db)):
    try:
        parsed = UUID(trial_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid trial id") from exc

    t = db.get(Trial, parsed)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")

    cond = db.get(Condition, t.condition_id)
    base = _trial_to_list_item(t)
    return TrialDetailOut(
        **base.model_dump(),
        condition_slug=cond.slug if cond else "",
        condition_name=cond.canonical_name if cond else "",
        primary_endpoint=t.primary_endpoint or "",
        locations=_locations_as_list(t.locations_json),
    )
