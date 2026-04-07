import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.entities import PasswordResetToken, User
from app.schemas.auth import (
    ForgotPasswordIn,
    LoginIn,
    RefreshIn,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
    UserLocalePatchIn,
    UserMeOut,
)
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _is_effective_admin(user: User) -> bool:
    owner = (settings.admin_owner_email or "").strip().lower()
    if owner and (user.email or "").strip().lower() == owner:
        return True
    return bool(user.is_admin)


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenOut)
def refresh_token(payload: RefreshIn, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token, expected_type="refresh")
        sub = data.get("sub")
        if not sub:
            raise ValueError("missing sub")
        user = db.get(User, UUID(str(sub)))
        if not user:
            raise ValueError("user not found")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user:
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expires = datetime.now(tz=timezone.utc) + timedelta(hours=settings.password_reset_token_hours)
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
        db.commit()
        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw}"
        background_tasks.add_task(send_password_reset_email, user.email, reset_url)
    return {"message": "If the account exists, a reset link will be sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    )
    now = datetime.now(tz=timezone.utc)
    if not row or row.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
    user.hashed_password = hash_password(payload.password)
    row.used_at = now
    db.commit()
    return {"message": "Password updated. You can sign in with your new password."}


@router.get("/me", response_model=UserMeOut)
def me(current_user: User = Depends(get_current_user)):
    loc: Literal["en", "he"] = "he" if current_user.preferred_locale == "he" else "en"
    return UserMeOut(
        id=str(current_user.id),
        email=current_user.email,
        is_admin=_is_effective_admin(current_user),
        preferred_locale=loc,
    )


@router.patch("/me", response_model=UserMeOut)
def patch_me(
    payload: UserLocalePatchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.preferred_locale = payload.preferred_locale
    db.commit()
    db.refresh(current_user)
    return UserMeOut(
        id=str(current_user.id),
        email=current_user.email,
        is_admin=_is_effective_admin(current_user),
        preferred_locale=payload.preferred_locale,
    )
