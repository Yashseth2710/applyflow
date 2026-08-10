"""Password hashing and JWT handling."""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()  # Argon2id, RFC 9106 low-memory defaults

TokenType = Literal["access", "refresh", "reset"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """False rather than raising, so callers can't leak why auth failed."""
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the hash used weaker parameters than the current config."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return False


def _create_token(
    subject: str,
    token_type: TokenType,
    expires: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
        # Per-token id, so refresh tokens can be revoked individually later.
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def password_fingerprint(password_hash: str) -> str:
    """A short, non-reversible marker of the password currently set.

    Carried in reset tokens so a link stops working the moment the password it
    was issued against changes. That is what makes the link single-use without
    storing anything: using it changes the hash, which changes the fingerprint,
    which no longer matches. Changing the password by any other route — the
    settings page, a second reset — invalidates outstanding links too, which is
    exactly what someone reaching for "reset my password" wants.

    The hash itself is never put in the token: a JWT is signed, not encrypted,
    so anyone holding the link can read every claim in it.
    """
    return hashlib.sha256(password_hash.encode()).hexdigest()[:32]


def create_reset_token(subject: str, password_hash: str) -> str:
    return _create_token(
        subject,
        "reset",
        timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        extra={"fp": password_fingerprint(password_hash)},
    )


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or the wrong type."""


def _decode(token: str, expected_type: TokenType) -> dict[str, Any]:
    payload: dict[str, Any]
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise TokenError("Wrong token type")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise TokenError("Invalid token subject")

    return payload


def decode_token(token: str, expected_type: TokenType) -> str:
    """Return the subject (user id) or raise TokenError.

    expected_type is enforced — otherwise a refresh token works as an access
    token and the short access lifetime means nothing.
    """
    return str(_decode(token, expected_type)["sub"])


def decode_reset_token(token: str, password_hash: str) -> str:
    """Return the subject, or raise TokenError if the link is no longer valid.

    Read the subject with `decode_token(token, "reset")` first to find the user
    whose hash to check against — the fingerprint cannot be verified without it.
    """
    payload = _decode(token, "reset")

    fingerprint = payload.get("fp")
    if not isinstance(fingerprint, str) or not hmac.compare_digest(
        fingerprint, password_fingerprint(password_hash)
    ):
        raise TokenError("This link has already been used")

    return str(payload["sub"])
