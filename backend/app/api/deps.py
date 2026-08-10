"""Shared FastAPI dependencies."""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenError, decode_token
from app.core.storage import Storage, build_storage
from app.models.user import User
from app.services.ai import AIProvider, build_provider

# auto_error=False so a missing header gives our own 401 shape, not FastAPI's.
_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_ai_provider() -> AIProvider:
    """The configured AI provider.

    A dependency so tests can pin it to the mock. Reading AI_PROVIDER directly
    would mean a developer's .env decided whether the suite called a live API.
    """
    return build_provider()


def get_storage(db: Session = Depends(get_db)) -> Storage:
    """The configured storage backend.

    A dependency rather than a module-level singleton because the database
    backend needs the request's session, and because tests override it.
    """
    return build_storage(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller from the bearer token.

    Same 401 for every failure — separating "no such user" from "bad token"
    lets someone probe which accounts exist.
    """
    if credentials is None or not credentials.credentials:
        raise _CREDENTIALS_ERROR

    try:
        subject = decode_token(credentials.credentials, expected_type="access")
        user_id = uuid.UUID(subject)
    except (TokenError, ValueError) as exc:
        raise _CREDENTIALS_ERROR from exc

    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_ERROR

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """The caller, if there is one. Never raises.

    For endpoints that answer everyone but can say more to someone signed in.
    Requiring a token there would turn a public endpoint into a private one,
    which breaks every existing caller for the sake of an extra field.
    """
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
