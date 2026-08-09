"""store uploaded files in the database

Revision ID: e3f38b83602a
Revises: fbf107f4a1f7
Create Date: 2026-08-09 16:49:04.019550

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f38b83602a"
down_revision: str | None = "fbf107f4a1f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column("key", sa.String(length=500), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(op.f("ix_stored_files_owner_id"), "stored_files", ["owner_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_stored_files_owner_id"), table_name="stored_files")
    op.drop_table("stored_files")
