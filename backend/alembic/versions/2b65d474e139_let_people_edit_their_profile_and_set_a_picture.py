"""let people edit their profile and set a picture

Revision ID: 2b65d474e139
Revises: ec392e43e6c9
Create Date: 2026-08-10 19:13:19.077883

The key points at a row in stored_files rather than holding bytes, so the
picture goes through the same storage the resumes do and survives a redeploy
on a host with an ephemeral filesystem.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2b65d474e139"
down_revision: str | None = "ec392e43e6c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("avatar_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    # The stored_files rows are left alone deliberately: they cascade from
    # users, so they are not orphaned, and dropping them here would make the
    # downgrade destroy pictures that an upgrade could otherwise restore.
    op.drop_column("profiles", "avatar_key")
