"""File bytes kept in the database."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StoredFile(Base):
    """One row per stored object, keyed by the same opaque string the storage
    interface uses everywhere else.

    Uploads are small and capped, and this keeps them atomic with the row that
    describes them — a file cannot outlive a rolled-back transaction, and both
    are covered by the same backup.
    """

    __tablename__ = "stored_files"

    key: Mapped[str] = mapped_column(String(500), primary_key=True)

    # Storage has no opinion about resumes, but it does need to know when the
    # bytes stop mattering. Hanging the row off the owner lets the database
    # clean up rather than relying on the application to remember.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<StoredFile {self.key} {self.size_bytes}B>"
