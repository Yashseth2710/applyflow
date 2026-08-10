"""User profile — career details that later feed the AI features."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import CareerLevel

if TYPE_CHECKING:
    from app.models.user import User


class Profile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(String(30))
    location: Mapped[str | None] = mapped_column(String(200))

    linkedin_url: Mapped[str | None] = mapped_column(Text)
    github_url: Mapped[str | None] = mapped_column(Text)
    portfolio_url: Mapped[str | None] = mapped_column(Text)

    # IANA name, captured from the browser at registration. Every timestamp is
    # stored UTC and rendered through this. See docs/architecture.md decision 4.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")

    career_level: Mapped[CareerLevel | None] = mapped_column(
        SAEnum(CareerLevel, name="career_level", values_callable=lambda e: [m.value for m in e])
    )
    years_experience: Mapped[int | None] = mapped_column(SmallInteger)
    summary: Mapped[str | None] = mapped_column(Text)

    # A key into storage, not the bytes themselves. The picture goes through
    # the same Storage abstraction as resumes, so it survives a redeploy on a
    # host with an ephemeral filesystem and is covered by the same backup.
    avatar_key: Mapped[str | None] = mapped_column(String(500))

    user: Mapped["User"] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile user={self.user_id}>"
