"""SQLAlchemy models.

Every model must be imported here so Alembic autogenerate sees it on
Base.metadata.
"""

from app.models.ai_output import AIOutput
from app.models.application import Application, ApplicationStatusHistory
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    CLOSED_STATUSES,
    INTERVIEW_STATUSES,
    SETTLED_OUTCOMES,
    ApplicationStatus,
    CareerLevel,
    EmploymentType,
    ExtractionStatus,
    InterviewMode,
    InterviewOutcome,
    InterviewRound,
    WorkMode,
)
from app.models.interview import Interview
from app.models.profile import Profile
from app.models.rate_event import RateEvent
from app.models.resume import Resume
from app.models.stored_file import StoredFile
from app.models.user import User

__all__ = [
    "CLOSED_STATUSES",
    "INTERVIEW_STATUSES",
    "SETTLED_OUTCOMES",
    "AIOutput",
    "Application",
    "ApplicationStatus",
    "ApplicationStatusHistory",
    "Base",
    "CareerLevel",
    "EmploymentType",
    "ExtractionStatus",
    "Interview",
    "InterviewMode",
    "InterviewOutcome",
    "InterviewRound",
    "Profile",
    "RateEvent",
    "Resume",
    "StoredFile",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "WorkMode",
]
