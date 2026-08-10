"""One row per attempt at something worth counting."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class RateEvent(Base, UUIDMixin):
    """A single recorded attempt, for limits that have to outlive the process.

    The in-memory limiter in `app/core/rate_limit.py` covers the cheap case:
    one address flooding one endpoint. It cannot cover anything that has to
    survive a restart, and on a host that sleeps when idle a restart is a
    routine event rather than an incident.

    Rows are tiny and short-lived. Each write prunes its own bucket, and
    occasionally sweeps everything past the retention window, so a burst of
    traffic against thousands of different keys does not leave a table behind.
    """

    __tablename__ = "rate_events"

    #: What is being counted, e.g. "login:someone@example.com" or "ai:<uuid>".
    #: Deliberately opaque: the caller decides what a bucket means, so adding a
    #: new limit does not need a schema change.
    bucket: Mapped[str] = mapped_column(String(200), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Every read is "how many in this bucket since t", so the index has to
        # carry both columns or each check scans the whole table.
        Index("ix_rate_events_bucket_created_at", "bucket", "created_at"),
    )

    def __repr__(self) -> str:
        # The bucket can contain an email address, which is why it is not here:
        # repr() ends up in logs and tracebacks.
        return f"<RateEvent {self.id}>"
