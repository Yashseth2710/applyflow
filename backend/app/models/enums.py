"""Enums shared across models.

These become native PostgreSQL enum types via Alembic. Adding a value later
requires a migration (ALTER TYPE ... ADD VALUE), which is a deliberate
trade-off: the database rejects invalid states rather than trusting the app.
"""

import enum


class CareerLevel(str, enum.Enum):
    """`str` mixin so Pydantic serialises the value, not `CareerLevel.STUDENT`."""

    STUDENT = "student"
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
