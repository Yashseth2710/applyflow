"""SQLAlchemy models.

Every model must be imported here so Alembic autogenerate sees it on
Base.metadata.
"""

from app.models.application import Application, ApplicationStatusHistory
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    CLOSED_STATUSES,
    INTERVIEW_STATUSES,
    ApplicationStatus,
    CareerLevel,
    EmploymentType,
    ExtractionStatus,
    WorkMode,
)
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.stored_file import StoredFile
from app.models.user import User

__all__ = [
    "CLOSED_STATUSES",
    "INTERVIEW_STATUSES",
    "Application",
    "ApplicationStatus",
    "ApplicationStatusHistory",
    "Base",
    "CareerLevel",
    "EmploymentType",
    "ExtractionStatus",
    "Profile",
    "Resume",
    "StoredFile",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "WorkMode",
]
