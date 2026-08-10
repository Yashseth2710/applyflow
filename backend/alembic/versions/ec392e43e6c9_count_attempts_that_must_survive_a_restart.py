"""count attempts that must survive a restart

Revision ID: ec392e43e6c9
Revises: f0377d89f5dc
Create Date: 2026-08-10 17:46:04.396803

Backs the durable half of rate limiting. The in-memory limiter forgets
everything when the process restarts, and it counts addresses, which is the
wrong unit for a guessing attack spread across many of them.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ec392e43e6c9"
down_revision: str | None = "f0377d89f5dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bucket", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Every read asks "how many in this bucket since t". Indexing the bucket
    # alone would still scan every attempt ever made against it.
    op.create_index(
        "ix_rate_events_bucket_created_at",
        "rate_events",
        ["bucket", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rate_events_bucket_created_at", table_name="rate_events")
    op.drop_table("rate_events")
