from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.db.session import get_db
from app.models.entities import (
    Bookmark,
    Condition,
    ResearchItem,
    ResearchItemAI,
    Source,
    Trial,
    User,
    UserFollowedCondition,
)
from app.services.follow_relevance import (
    audience_from_trial_ages,
    combined_personalization_multiplier,
    countries_for_item,
    countries_for_trial_row,
    infer_item_audience,
)
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


def _effective_follow_prefs(
    db: Session,
    *,
    user: User | None,
    condition_id,
    age_scope: str | None,
    geography: str | None,
) -> tuple[str, str]:
    eff_age, eff_geo = age_scope, geography
    if user:
        follow = db.scalar(
            select(UserFollowedCondition).where(
                UserFollowedCondition.user_id == user.id,
                UserFollowedCondition.condition_id == condition_id,
            )
        )
        if follow:
            if eff_age is None:
                eff_age = follow.age_scope
            if eff_geo is None:
                eff_geo = follow.geography
    return (eff_age or "both"), (eff_geo or "global")


def _personalize_research_items(
    db: Session,
    pool: list[ResearchItem],
    *,
    age_scope: str,
    geography: str,
) -> list[ResearchItem]:
    if not pool:
        return pool
    us = age_scope.strip().lower()
    geo = (geography or "global").strip()
    if us == "both" and geo.lower() in ("", "global", "worldwide"):
        return pool

    ids = [i.id for i in pool]
    ais = {
        r.research_item_id: r
        for r in db.scalars(select(ResearchItemAI).where(ResearchItemAI.research_item_id.in_(ids))).all()
    }
    trials = list(db.scalars(select(Trial).where(Trial.research_item_id.in_(ids))).all())
    trial_by = {t.research_item_id: t for t in trials if t.research_item_id}

    scored: list[tuple[float, float, ResearchItem]] = []
    for item in pool:
        ai = ais.get(item.id)
        tr = trial_by.get(item.id)
        aud = infer_item_audience(item, ai, tr)
        cc = countries_for_item(item, tr)
        mult = combined_personalization_multiplier(
            user_age_scope=age_scope,
            user_geography=geography,
            item_audience=aud,
            countries=cc,
        )
        ts = item.published_at.timestamp() if item.published_at else 0.0
        scored.append((mult, ts, item))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [t[2] for t in scored]


@router.get("/conditions/by-slug/{slug}/updates", response_model=ResearchUpdatesPage)
def list_condition_updates(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    item_type: str | None = Query(None, description="Filter by item_type e.g. paper, trial, regulatory"),
    locale: Literal["en", "he"] = Query(default="en", description="UI locale for Hebrew recaps when stored"),
    age_scope: str | None = Query(None, description="Override age focus: pediatric, adult, both"),
    geography: str | None = Query(None, description="Override region hint for ranking e.g. Israel"),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    eff_age, eff_geo = _effective_follow_prefs(
        db, user=current_user, condition_id=condition.id, age_scope=age_scope, geography=geography
    )
    use_personal = (eff_age.lower() != "both") or (eff_geo.strip().lower() not in ("", "global", "worldwide"))

    count_stmt = select(func.count()).select_from(ResearchItem).where(ResearchItem.condition_id == condition.id)
    list_stmt = select(ResearchItem).where(ResearchItem.condition_id == condition.id)
    if item_type:
        count_stmt = count_stmt.where(ResearchItem.item_type == item_type)
        list_stmt = list_stmt.where(ResearchItem.item_type == item_type)

    total = db.scalar(count_stmt) or 0

    if use_personal and total > 0:
        cap = min(600, max(offset + limit + 40, 120))
        pool = list(
            db.scalars(list_stmt.order_by(ResearchItem.published_at.desc()).limit(cap)).all()
        )
        ranked = _personalize_research_items(db, pool, age_scope=eff_age, geography=eff_geo)
        items = ranked[offset : offset + limit]
    else:
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
    current_user: User | None = Depends(get_optional_user),
    recruiting_only: bool = False,
    phase: str | None = Query(None, description="Substring match on phase, e.g. 2"),
    limit: int = Query(50, ge=1, le=100),
    age_scope: str | None = Query(None, description="Override age focus for ranking: pediatric, adult, both"),
    geography: str | None = Query(None, description="Override region hint for ranking"),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")

    eff_age, eff_geo = _effective_follow_prefs(
        db, user=current_user, condition_id=condition.id, age_scope=age_scope, geography=geography
    )
    use_personal = (eff_age.lower() != "both") or (eff_geo.strip().lower() not in ("", "global", "worldwide"))

    q = select(Trial).where(Trial.condition_id == condition.id)
    if recruiting_only:
        q = q.where(Trial.status.ilike("%recruit%"))
    if phase:
        q = q.where(Trial.phase.ilike(f"%{phase}%"))

    fetch_limit = min(160, limit * 4) if use_personal else limit
    rows = list(db.scalars(q.order_by(Trial.last_verified_at.desc()).limit(fetch_limit)).all())

    if use_personal and rows:
        scored: list[tuple[float, float, Trial]] = []
        for t in rows:
            aud = audience_from_trial_ages(t.age_min, t.age_max)
            countries = countries_for_trial_row(t)
            mult = combined_personalization_multiplier(
                user_age_scope=eff_age,
                user_geography=eff_geo,
                item_audience=aud,
                countries=countries,
            )
            ts = t.last_verified_at.timestamp() if t.last_verified_at else 0.0
            scored.append((mult, ts, t))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        rows = [x[2] for x in scored[:limit]]
    else:
        rows = rows[:limit]

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
