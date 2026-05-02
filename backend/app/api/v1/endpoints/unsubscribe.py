from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.security import decode_digest_unsubscribe_token
from app.db.session import get_db
from app.models.entities import User
from app.schemas.unsubscribe import DigestUnsubscribeIn
from app.services.digest_unsubscribe import disable_digest_email_for_user

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])

_HTML_OK_EN = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Unsubscribed</title></head>
<body style="font-family:system-ui,sans-serif;max-width:36rem;margin:3rem auto;padding:0 1rem;line-height:1.5;color:#334155;">
<p style="font-size:1.125rem;font-weight:600;color:#0b213f;">You are unsubscribed from research briefing emails.</p>
<p>You can turn email briefings back on anytime in the app under Settings → Research briefings &amp; notifications.</p>
<p style="font-size:0.875rem;color:#94a3b8;">— CureCompass</p>
</body>
</html>"""


def _apply_unsubscribe(db: Session, token: str) -> None:
    try:
        sub = decode_digest_unsubscribe_token(token)
        user_id = UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired unsubscribe link.",
        ) from exc
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid unsubscribe link.")
    disable_digest_email_for_user(db, user_id)
    db.commit()


@router.post("/digest")
def unsubscribe_digest_post(payload: DigestUnsubscribeIn, db: Session = Depends(get_db)):
    """Public: turn off research-briefing email for the account tied to the signed token."""
    _apply_unsubscribe(db, payload.token)
    return {"ok": True, "message": "Research briefing emails are turned off for your account."}


@router.get("/digest", response_class=HTMLResponse)
def unsubscribe_digest_get(
    token: str = Query(..., min_length=10),
    db: Session = Depends(get_db),
):
    """Same as POST, for one-click from email clients and plain links (no JavaScript)."""
    _apply_unsubscribe(db, token)
    return HTMLResponse(content=_HTML_OK_EN, status_code=200)
