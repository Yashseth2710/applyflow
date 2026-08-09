"""Uploaded resume files and their versions."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ExtractionStatus

if TYPE_CHECKING:
    from app.models.user import User


class Resume(Base, UUIDMixin, TimestampMixin):
    """One row per uploaded file.

    Versions are rows sharing a family_id rather than a separate versions table.
    An application records the exact file that was sent, so it has to be able to
    point at a specific version — which means versions need their own ids, which
    means they may as well be the rows.
    """

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Shared by every version of the same resume. The first version sets this to
    # its own id, so a family is never orphaned by deleting a "parent" row.
    family_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # The version the user considers current. Exactly one per family, maintained
    # by the service — a partial unique index would block the moment between
    # clearing the old flag and setting the new one.
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # sha256 of the bytes. Lets us spot a re-upload of an identical file and
    # verify what came back out of storage is what went in.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Opaque to the app — only the storage backend interprets it.
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)

    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        SAEnum(
            ExtractionStatus,
            name="extraction_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ExtractionStatus.PENDING,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extraction_error: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("family_id", "version", name="uq_resumes_family_version"),
        Index("ix_resumes_user_created", "user_id", "created_at"),
        # The list view shows current versions only; history is fetched per family.
        Index("ix_resumes_user_family", "user_id", "family_id"),
    )

    @property
    def page_count_hint(self) -> int | None:
        """Rough page count from the extracted text, or None if there is none.

        Only a hint — used for a "looks like 3 pages" label, never for anything
        that has to be right.
        """
        if not self.extracted_text:
            return None
        return max(1, round(len(self.extracted_text) / 3000))

    def __repr__(self) -> str:
        return f"<Resume {self.id} {self.title} v{self.version}>"
