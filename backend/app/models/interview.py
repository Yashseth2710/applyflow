"""Interview rounds attached to an application."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import InterviewMode, InterviewOutcome, InterviewRound

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


def _pg_enum(enum_cls: type, name: str) -> SAEnum:
    """Store the enum *values* ("phone_screen"), not the member names."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Interview(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised, like status history: ownership checks stay one indexed
    # predicate instead of a join back through applications.
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    round: Mapped[InterviewRound] = mapped_column(
        _pg_enum(InterviewRound, "interview_round"), nullable=False
    )
    mode: Mapped[InterviewMode | None] = mapped_column(_pg_enum(InterviewMode, "interview_mode"))

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    # A room, an address or a meeting link — one field because in practice
    # people paste whichever one they were sent.
    location: Mapped[str | None] = mapped_column(Text)
    interviewer: Mapped[str | None] = mapped_column(String(200))

    # Written before: what to revise, questions to ask.
    notes: Mapped[str | None] = mapped_column(Text)
    # Written after: how it actually went.
    feedback: Mapped[str | None] = mapped_column(Text)

    outcome: Mapped[InterviewOutcome] = mapped_column(
        _pg_enum(InterviewOutcome, "interview_outcome"),
        nullable=False,
        default=InterviewOutcome.PENDING,
    )

    application: Mapped["Application"] = relationship(back_populates="interviews")
    user: Mapped["User"] = relationship()

    __table_args__ = (
        # Both reminder queries and the upcoming list sort by time within a user.
        Index("ix_interviews_user_scheduled", "user_id", "scheduled_at"),
        Index("ix_interviews_user_outcome", "user_id", "outcome"),
    )

    def __repr__(self) -> str:
        return f"<Interview {self.id} {self.round} {self.scheduled_at:%Y-%m-%d}>"
