"""Resume request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ExtractionStatus


def _blank_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    return v.strip() or None


class ResumeUpdate(BaseModel):
    """Only the metadata is editable. Replacing the file means a new version."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, v: str | None) -> str | None:
        return _blank_to_none(v)


class ResumeResponse(BaseModel):
    """Deliberately without extracted_text — it runs to tens of thousands of
    characters and no list view shows it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    family_id: uuid.UUID
    version: int
    is_current: bool
    title: str
    notes: str | None
    original_filename: str
    content_type: str
    size_bytes: int
    extraction_status: ExtractionStatus
    extraction_error: str | None
    created_at: datetime
    updated_at: datetime


class ResumeDetailResponse(ResumeResponse):
    extracted_text: str | None
    versions: list[ResumeResponse] = []


class ResumeUploadResponse(ResumeResponse):
    """The stored resume, plus anything the user should know about it.

    duplicate_of is a warning rather than a rejection — uploading the same file
    under two titles is a reasonable thing to do, so the choice stays with the
    user.
    """

    duplicate_of_id: uuid.UUID | None = None
    duplicate_of_title: str | None = None


class ResumeUsageResponse(BaseModel):
    application_count: int


class ResumeTextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extraction_status: ExtractionStatus
    extracted_text: str | None
    extraction_error: str | None
