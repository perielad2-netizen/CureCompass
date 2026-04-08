from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
optional_bearer = HTTPBearer(auto_error=False)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing subject")
        parsed = UUID(user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc

    user = db.get(User, parsed)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_owner_admin_user(user: User = Depends(get_current_user)) -> User:
    owner = (settings.admin_owner_email or "").strip().lower()
    email = (user.email or "").strip().lower()
    # If an owner email is configured, that account is the sole admin gate.
    if owner:
        if email != owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner-only admin access required")
        return user
    # Fallback for environments that have no configured owner email.
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def user_is_effective_admin(user: User) -> bool:
    """Matches /auth/me: owner email from settings, else DB is_admin."""
    owner = (settings.admin_owner_email or "").strip().lower()
    if owner and (user.email or "").strip().lower() == owner:
        return True
    return bool(user.is_admin)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.get(User, UUID(user_id))
    except Exception:  # noqa: BLE001
        return None
