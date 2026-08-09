"""Interview and reminder schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    ApplicationStatus,
    InterviewMode,
    InterviewOutcome,
    InterviewRound,
)


def _blank_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    return v.strip() or None


class InterviewBase(BaseModel):
    round: InterviewRound
    mode: InterviewMode | None = None
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    location: str | None = None
    interviewer: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    feedback: str | None = None

    @field_validator("location", "interviewer", "notes", "feedback")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        """A naive datetime would be silently read as UTC, which quietly moves
        every interview for a user in IST."""
        if v.tzinfo is None:
            raise ValueError("scheduled_at must include a timezone offset")
        return v


class InterviewCreate(InterviewBase):
    application_id: uuid.UUID
    outcome: InterviewOutcome = InterviewOutcome.PENDING


class InterviewUpdate(BaseModel):
    """PATCH semantics. The application it belongs to is deliberately absent —
    moving an interview between applications would rewrite history."""

    model_config = ConfigDict(extra="forbid")

    round: InterviewRound | None = None
    mode: InterviewMode | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    location: str | None = None
    interviewer: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    feedback: str | None = None
    outcome: InterviewOutcome | None = None

    @field_validator("location", "interviewer", "notes", "feedback")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return _blank_to_none(v)

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("scheduled_at must include a timezone offset")
        return v


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    round: InterviewRound
    mode: InterviewMode | None
    scheduled_at: datetime
    duration_minutes: int | None
    location: str | None
    interviewer: str | None
    notes: str | None
    feedback: str | None
    outcome: InterviewOutcome
    created_at: datetime
    updated_at: datetime


class InterviewWithApplication(InterviewResponse):
    """For lists that aren't already inside one application, where "Acme —
    Backend Engineer" is the only thing that makes a row meaningful."""

    company_name: str
    job_title: str
    application_status: ApplicationStatus


ReminderKind = Literal["interview_upcoming", "interview_needs_outcome", "application_stale"]
ReminderSeverity = Literal["info", "warning"]


class Reminder(BaseModel):
    """Worked out from the data on each request rather than stored.

    A reminders table would need a scheduler to fill it and would go stale the
    moment an interview moved; derived ones cannot disagree with the data.
    """

    kind: ReminderKind
    severity: ReminderSeverity
    title: str
    detail: str
    application_id: uuid.UUID
    interview_id: uuid.UUID | None = None
    #: What the reminder is about — an interview time, or the date things went
    #: quiet. Lets the client sort without knowing each kind's rules.
    occurs_at: datetime


class ReminderList(BaseModel):
    items: list[Reminder]
    total: int
