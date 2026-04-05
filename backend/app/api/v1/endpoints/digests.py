import smtplib
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entities import Condition, Digest, User
from app.schemas.digest_api import DigestDetailOut, DigestGenerateIn, DigestSummaryOut
from app.services.digest_service import DigestService
from app.services.email import send_digest_email

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("", response_model=list[DigestSummaryOut])
def list_digests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    rows = db.scalars(
        select(Digest)
        .where(Digest.user_id == current_user.id)
        .order_by(Digest.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    out: list[DigestSummaryOut] = []
    for d in rows:
        cond = db.get(Condition, d.condition_id)
        out.append(
            DigestSummaryOut(
                id=str(d.id),
                digest_type=d.digest_type,
                title=d.title,
                condition_slug=cond.slug if cond else "",
                condition_name=cond.canonical_name if cond else "",
                created_at=d.created_at,
                email_delivered=d.delivered_at is not None,
            )
        )
    return out


@router.post("/generate")
def generate_digests(
    payload: DigestGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DigestService(db)
    slugs = payload.condition_slugs
    filter_slugs: list[str] | None = slugs if len(slugs) > 0 else None
    rows = svc.generate_for_user(
        current_user,
        payload.digest_type,
        filter_slugs,
        force=True,
    )
    db.commit()
    return {
        "generated": len(rows),
        "ids": [str(r.id) for r in rows],
    }


@router.post("/{digest_id}/email")
def email_digest(
    digest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send this briefing to the signed-in user's email (same SMTP as scheduled digests)."""
    try:
        parsed = UUID(digest_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid digest id") from exc

    row = db.get(Digest, parsed)
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digest not found")

    try:
        ok = send_digest_email(current_user.email, row.title, row.body_markdown)
    except smtplib.SMTPAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SMTP login failed. For Gmail, turn on 2-Step Verification and use a 16-character App Password "
                "as SMTP_PASSWORD (not your normal Google account password)."
            ),
        ) from exc
    except smtplib.SMTPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The mail server rejected the send: {exc!s}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Could not reach the mail server. Check SMTP_HOST and SMTP_PORT "
                "(Gmail: smtp.gmail.com, 587). Ensure .env has only one SMTP_HOST line—"
                "a duplicate `SMTP_HOST=localhost` above Gmail settings connects to localhost and fails."
            ),
        ) from exc

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SMTP is not configured. Set SMTP_HOST in the API .env "
                "(for local testing use MailHog or Mailpit on port 1025), then restart the API."
            ),
        )

    row.delivered_at = datetime.now(tz=timezone.utc)
    db.commit()
    return {"sent": True}


@router.get("/{digest_id}", response_model=DigestDetailOut)
def get_digest(
    digest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed = UUID(digest_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid digest id") from exc

    row = db.get(Digest, parsed)
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digest not found")

    cond = db.get(Condition, row.condition_id)
    return DigestDetailOut(
        id=str(row.id),
        digest_type=row.digest_type,
        title=row.title,
        condition_slug=cond.slug if cond else "",
        condition_name=cond.canonical_name if cond else "",
        created_at=row.created_at,
        email_delivered=row.delivered_at is not None,
        body_markdown=row.body_markdown,
        structured_json=row.structured_json or {},
    )


@router.delete("/{digest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_digest(
    digest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed = UUID(digest_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid digest id") from exc

    row = db.get(Digest, parsed)
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digest not found")

    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
