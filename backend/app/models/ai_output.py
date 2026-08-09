"""Cached AI generations."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.services.ai.prompts import AITask

if TYPE_CHECKING:
    from app.models.application import Application


class AIOutput(Base, UUIDMixin, TimestampMixin):
    """One generation per application per task.

    Cached because a generation costs real seconds and real quota. Without this,
    opening an application would regenerate everything every time.
    """

    __tablename__ = "ai_outputs"

    application_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task: Mapped[AITask] = mapped_column(
        SAEnum(AITask, name="ai_task", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    # Structured tasks land here; the cover letter is prose and uses `text`.
    content: Mapped[dict | None] = mapped_column(JSONB)
    text: Mapped[str | None] = mapped_column(Text)

    # Which inputs produced this. When the job description or the attached
    # resume changes, the cached answer is about the old text and is offered as
    # stale rather than silently shown as current.
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)

    #: Kept so the UI can say when it was written, separately from edits.
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    application: Mapped["Application"] = relationship(back_populates="ai_outputs")

    __table_args__ = (
        UniqueConstraint("application_id", "task", name="uq_ai_outputs_application_task"),
        Index("ix_ai_outputs_user_task", "user_id", "task"),
    )

    def __repr__(self) -> str:
        return f"<AIOutput {self.task} for {self.application_id}>"
