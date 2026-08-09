"""add resumes

Revision ID: fbf107f4a1f7
Revises: 5eced8124917
Create Date: 2026-08-09 16:17:08.498717

Hand-edited: autogenerate declared the enum inline and left the new foreign key
unnamed, which downgrade then cannot drop.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "fbf107f4a1f7"
down_revision: str | None = "5eced8124917"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


extraction_status = postgresql.ENUM(
    "pending", "ok", "empty", "failed", name="extraction_status", create_type=False
)

RESUME_FK = "fk_applications_resume_id_resumes"


def upgrade() -> None:
    bind = op.get_bind()
    extraction_status.create(bind, checkfirst=True)

    op.create_table(
        "resumes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("extraction_status", extraction_status, nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id", "version", name="uq_resumes_family_version"),
    )
    op.create_index(op.f("ix_resumes_content_hash"), "resumes", ["content_hash"])
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"])
    op.create_index("ix_resumes_user_created", "resumes", ["user_id", "created_at"])
    op.create_index("ix_resumes_user_family", "resumes", ["user_id", "family_id"])

    # applications.resume_id has existed since the applications migration, but
    # had nothing to point at until now.
    op.create_foreign_key(
        RESUME_FK,
        "applications",
        "resumes",
        ["resume_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(RESUME_FK, "applications", type_="foreignkey")

    op.drop_index("ix_resumes_user_family", table_name="resumes")
    op.drop_index("ix_resumes_user_created", table_name="resumes")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    op.drop_index(op.f("ix_resumes_content_hash"), table_name="resumes")
    op.drop_table("resumes")

    extraction_status.drop(op.get_bind(), checkfirst=True)
