"""Authentication request/response schemas."""

import uuid
import zoneinfo
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings
from app.models.enums import CareerLevel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        # Capped because Argon2 hashes the whole input; an unbounded password
        # is a cheap way to burn CPU on every login attempt.
        max_length=128,
        description="At least 8 characters",
    )
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    timezone: str | None = Field(
        default=None,
        max_length=64,
        description="IANA timezone from the browser, e.g. Asia/Kolkata",
    )

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        """Lowercased so 'A@b.com' and 'a@b.com' cannot become two accounts."""
        return v.strip().lower()

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        """Reject unknown zone names rather than storing junk that breaks
        rendering later."""
        if v is None:
            return None
        try:
            zoneinfo.ZoneInfo(v)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            return settings.DEFAULT_TIMEZONE
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    """The refresh token is intentionally absent — it is delivered as an
    httpOnly cookie so JavaScript can never read it."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timezone: str
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    career_level: CareerLevel | None = None
    years_experience: int | None = None
    summary: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
    profile: ProfileResponse | None = None

    #: The profile picture, inlined as a data URI, or None when there is none
    #: and the client should fall back to initials.
    #:
    #: Not a URL. The access token lives in memory and travels as a header, so
    #: a plain `<img src>` would arrive unauthenticated and get a 401 — the
    #: same trap already hit once with resume downloads.
    avatar: str | None = None


class AuthResponse(BaseModel):
    """Returned by register and login: the user plus their access token."""

    user: UserResponse
    token: TokenResponse
