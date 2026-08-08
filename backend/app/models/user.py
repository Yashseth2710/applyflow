"""User account model."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    # Emails are normalised to lowercase before they reach the database (see
    # schemas/auth.py). A plain unique index on the normalised value avoids
    # depending on the citext extension, which keeps local, CI and Neon
    # identical with no extension setup.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["Profile"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        # Deliberately excludes email — repr() lands in logs and tracebacks.
        return f"<User {self.id}>"
