"""cache ai generations

Revision ID: f0377d89f5dc
Revises: c104d870d14c
Create Date: 2026-08-10 02:58:31.117402

Hand-edited: autogenerate declares the enum inline, leaving nothing to drop on
downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f0377d89f5dc"
down_revision: str | None = "c104d870d14c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ai_task = postgresql.ENUM(
    "jd_analysis",
    "resume_match",
    "cover_letter",
    "interview_questions",
    name="ai_task",
    create_type=False,
)


def upgrade() -> None:
    ai_task.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_outputs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("task", ai_task, nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "task", name="uq_ai_outputs_application_task"),
    )
    op.create_index(op.f("ix_ai_outputs_application_id"), "ai_outputs", ["application_id"])
    op.create_index(op.f("ix_ai_outputs_user_id"), "ai_outputs", ["user_id"])
    op.create_index("ix_ai_outputs_user_task", "ai_outputs", ["user_id", "task"])


def downgrade() -> None:
    op.drop_index("ix_ai_outputs_user_task", table_name="ai_outputs")
    op.drop_index(op.f("ix_ai_outputs_user_id"), table_name="ai_outputs")
    op.drop_index(op.f("ix_ai_outputs_application_id"), table_name="ai_outputs")
    op.drop_table("ai_outputs")

    ai_task.drop(op.get_bind(), checkfirst=True)
