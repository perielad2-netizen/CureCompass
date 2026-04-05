from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Bookmark, Condition, ResearchItem, Source, User
from app.schemas.bookmarks import BookmarkListItem, BookmarkToggleOut
from app.services.research_presenter import serialize_research_item

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("", response_model=list[BookmarkListItem])
def list_bookmarks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    locale: Literal["en", "he"] = Query(default="en"),
):
    rows = db.scalars(
        select(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at.desc())
    ).all()
    out: list[BookmarkListItem] = []
    for b in rows:
        item = db.get(ResearchItem, b.research_item_id)
        if not item:
            continue
        cond = db.get(Condition, item.condition_id)
        core = serialize_research_item(db, item, locale=locale)
        src = db.get(Source, item.source_id)
        summary = core["summary"]
        if len(summary) > 400:
            summary = summary[:400] + "…"
        out.append(
            BookmarkListItem(
                research_item_id=str(b.research_item_id),
                created_at=b.created_at,
                condition_slug=cond.slug if cond else "",
                title=item.title,
                source_name=src.name if src else "Source",
                source_url=item.source_url,
                evidence_stage_label=core["evidence_stage_label"],
                summary=summary,
                recap_locale=core["recap_locale"],
            )
        )
    return out


@router.post("/{research_item_id}", response_model=BookmarkToggleOut)
def add_bookmark(
    research_item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rid = UUID(research_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid research item id") from exc

    item = db.get(ResearchItem, rid)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research item not found")

    existing = db.scalar(
        select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.research_item_id == rid)
    )
    if existing:
        return BookmarkToggleOut(
            research_item_id=str(rid),
            bookmarked=True,
            created_at=existing.created_at.isoformat(),
        )

    row = Bookmark(user_id=current_user.id, research_item_id=rid)
    db.add(row)
    db.commit()
    db.refresh(row)
    return BookmarkToggleOut(
        research_item_id=str(rid),
        bookmarked=True,
        created_at=row.created_at.isoformat(),
    )


@router.delete("/{research_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(
    research_item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rid = UUID(research_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid research item id") from exc

    row = db.scalar(select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.research_item_id == rid))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
