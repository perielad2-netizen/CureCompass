from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire, "typ": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "exp": expire, "typ": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str, *, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if expected_type and payload.get("typ") != expected_type:
        raise ValueError("Invalid token type")
    return payload


def create_digest_unsubscribe_token(subject: str) -> str:
    """Long-lived signed token for one-click email unsubscribe (research briefings only)."""
    expire = datetime.now(tz=timezone.utc) + timedelta(days=settings.digest_unsubscribe_token_days)
    payload = {"sub": subject, "exp": expire, "typ": "digest_unsubscribe"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_digest_unsubscribe_token(token: str) -> str:
    data = decode_token(token, expected_type="digest_unsubscribe")
    sub = data.get("sub")
    if not sub:
        raise ValueError("Invalid token")
    return str(sub)
