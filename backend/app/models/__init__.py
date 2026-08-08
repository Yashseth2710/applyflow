"""SQLAlchemy models.

Every model must be imported here so Alembic autogenerate can see it on
Base.metadata. Milestone 2 adds User and Profile.
"""

from app.models.base import Base, TimestampMixin, UUIDMixin

__all__ = ["Base", "TimestampMixin", "UUIDMixin"]
