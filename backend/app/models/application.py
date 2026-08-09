"""Job application — the central record of the product."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ApplicationStatus, EmploymentType, WorkMode

if TYPE_CHECKING:
    from app.models.user import User


def _pg_enum(enum_cls: type, name: str) -> SAEnum:
    """Store the enum *values* ("full_time"), not the member names ("FULL_TIME")."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Application(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Inline rather than a shared companies table: dedup ("Google" vs "Google
    # India" vs "google") is easy to get wrong and corrupts everyone's data.
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_website: Mapped[str | None] = mapped_column(Text)

    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    job_description: Mapped[str | None] = mapped_column(Text)
    job_url: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))

    work_mode: Mapped[WorkMode | None] = mapped_column(_pg_enum(WorkMode, "work_mode"))
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        _pg_enum(EmploymentType, "employment_type")
    )

    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    status: Mapped[ApplicationStatus] = mapped_column(
        _pg_enum(ApplicationStatus, "application_status"),
        nullable=False,
        default=ApplicationStatus.WISHLIST,
    )

    # Free text, not an enum — a fixed list just makes people pick "other".
    source: Mapped[str | None] = mapped_column(String(100))

    # SET NULL, not CASCADE: deleting a resume must not delete the history of
    # applications it was used for.
    resume_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    date_posted: Mapped[date | None] = mapped_column(Date)
    date_applied: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Ordering within a board column. Sparse (gaps allowed) so a drag only has
    # to rewrite the moved card, not renumber the whole column.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship()
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at",
    )

    __table_args__ = (
        # Every list query filters by user_id and usually by status too.
        Index("ix_applications_user_status", "user_id", "status"),
        Index("ix_applications_user_created", "user_id", "created_at"),
        Index("ix_applications_user_position", "user_id", "status", "position"),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_applications_salary_range",
        ),
    )

    def __repr__(self) -> str:
        return f"<Application {self.id} {self.status}>"


class ApplicationStatusHistory(Base, UUIDMixin):
    """Append-only log of status changes.

    Conversion rates and time-in-stage need the journey, not just the current
    status, and it can't be reconstructed later — so record it from the start.
    """

    __tablename__ = "application_status_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised so ownership checks are one indexed predicate, not a join.
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # NULL on the first entry, which records the status the application was
    # created with.
    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        _pg_enum(ApplicationStatus, "application_status")
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        _pg_enum(ApplicationStatus, "application_status"), nullable=False
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    application: Mapped["Application"] = relationship(back_populates="status_history")

    def __repr__(self) -> str:
        return f"<StatusHistory {self.from_status} -> {self.to_status}>"
