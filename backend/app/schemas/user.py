"""Account and profile request schemas."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CareerLevel

#: Feeds the AI prompts, so it is a paragraph rather than a document.
MAX_SUMMARY_CHARS = 2_000
MAX_URL_CHARS = 2_000


def _blank_to_none(v: str | None) -> str | None:
    """An emptied text input arrives as "". Clearing a field has to mean NULL,
    or "no value" ends up with two representations that sort and compare
    differently."""
    if v is None:
        return None
    return v.strip() or None


class ProfileUpdate(BaseModel):
    """PATCH semantics: only what was sent is changed.

    Email is deliberately absent. Changing it needs a verify-the-new-address
    flow and somewhere to send mail from, and accepting a new address without
    proving it is reachable would lock people out of their own accounts.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)

    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=200)

    linkedin_url: str | None = Field(default=None, max_length=MAX_URL_CHARS)
    github_url: str | None = Field(default=None, max_length=MAX_URL_CHARS)
    portfolio_url: str | None = Field(default=None, max_length=MAX_URL_CHARS)

    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    career_level: CareerLevel | None = None
    years_experience: int | None = Field(default=None, ge=0, le=70)
    summary: str | None = Field(default=None, max_length=MAX_SUMMARY_CHARS)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("phone", "location", "linkedin_url", "github_url", "portfolio_url", "summary")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, v: str | None) -> str | None:
        """Checked against the system's zone database rather than accepted as
        text. A typo here silently shifts every timestamp on the site, and it
        would look like the data was wrong rather than the setting."""
        if v is None:
            return None

        candidate = v.strip()
        try:
            ZoneInfo(candidate)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("not a known timezone") from exc
        return candidate


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    # Same rules as registration. Argon2 hashes the whole input, so an
    # unbounded password is a cheap way to burn CPU on every sign-in.
    new_password: str = Field(min_length=8, max_length=128)


class AccountDelete(BaseModel):
    """Deleting takes the password as well as the session.

    It is irreversible and it takes everything, so an unattended laptop should
    not be enough on its own.
    """

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)
