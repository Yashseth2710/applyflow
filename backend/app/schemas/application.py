"""Application request/response schemas."""

import uuid
from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ApplicationStatus, EmploymentType, WorkMode

T = TypeVar("T")

#: A long job posting runs to a few thousand characters. Fifty thousand is far
#: beyond any real one and still bounded, which the underlying TEXT column is
#: not — uncapped, a single request can write as much as it likes into a 500 MB
#: database, and no per-file upload limit goes anywhere near that path.
MAX_DESCRIPTION_CHARS = 50_000

#: URLs. Browsers stop honouring them well before this.
MAX_URL_CHARS = 2_000


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def _blank_to_none(v: str | None) -> str | None:
    """An empty text input arrives as "" — store NULL instead, so "no value"
    has one representation rather than two."""
    if v is None:
        return None
    stripped = v.strip()
    return stripped or None


class ApplicationBase(BaseModel):
    company_name: Annotated[str, Field(min_length=1, max_length=200)]
    job_title: Annotated[str, Field(min_length=1, max_length=200)]

    company_website: str | None = Field(default=None, max_length=MAX_URL_CHARS)
    job_description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_CHARS)
    job_url: str | None = Field(default=None, max_length=MAX_URL_CHARS)
    location: str | None = Field(default=None, max_length=200)

    work_mode: WorkMode | None = None
    employment_type: EmploymentType | None = None

    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str = Field(default="INR", min_length=3, max_length=3)

    source: str | None = Field(default=None, max_length=100)
    resume_id: uuid.UUID | None = None

    date_posted: date | None = None
    date_applied: datetime | None = None

    @field_validator("company_name", "job_title")
    @classmethod
    def strip_required(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("company_website", "job_url", "job_description", "location", "source")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("salary_currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def check_salary_range(self) -> "ApplicationBase":
        """Mirrors the database CHECK constraint, so the user gets a 422 with a
        clear message instead of a 500 from a constraint violation."""
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot be greater than salary_max")
        return self


class ApplicationCreate(ApplicationBase):
    status: ApplicationStatus = ApplicationStatus.WISHLIST


class ApplicationUpdate(BaseModel):
    """All fields optional — PATCH semantics.

    Status is deliberately absent: it goes through PATCH /{id}/status so every
    change is recorded in the history table. Allowing it here would let a
    generic update silently bypass that.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    company_website: str | None = Field(default=None, max_length=MAX_URL_CHARS)
    job_description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_CHARS)
    job_url: str | None = Field(default=None, max_length=MAX_URL_CHARS)
    location: str | None = Field(default=None, max_length=200)
    work_mode: WorkMode | None = None
    employment_type: EmploymentType | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    source: str | None = Field(default=None, max_length=100)
    resume_id: uuid.UUID | None = None
    date_posted: date | None = None
    date_applied: datetime | None = None
    position: int | None = Field(default=None, ge=0)

    @field_validator("company_name", "job_title")
    @classmethod
    def strip_required(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("company_website", "job_url", "job_description", "location", "source")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("salary_currency")
    @classmethod
    def upper_currency(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    # Optional, so a Kanban drag can set both column and ordering in one call.
    position: int | None = Field(default=None, ge=0)


class StatusHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    changed_at: datetime


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    company_website: str | None
    job_title: str
    job_description: str | None
    job_url: str | None
    location: str | None
    work_mode: WorkMode | None
    employment_type: EmploymentType | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str
    status: ApplicationStatus
    source: str | None
    resume_id: uuid.UUID | None
    date_posted: date | None
    date_applied: datetime | None
    position: int
    created_at: datetime
    updated_at: datetime


class ApplicationDetailResponse(ApplicationResponse):
    """Detail view adds the journey. Excluded from list responses because it
    would mean N extra queries for data the list never shows."""

    status_history: list[StatusHistoryEntry] = []


class BoardColumn(BaseModel):
    status: ApplicationStatus
    count: int
    items: list[ApplicationResponse]


class BoardResponse(BaseModel):
    columns: list[BoardColumn]
    total: int


SortField = Literal[
    "created_at",
    "updated_at",
    "date_applied",
    "company_name",
    "job_title",
]
SortOrder = Literal["asc", "desc"]
