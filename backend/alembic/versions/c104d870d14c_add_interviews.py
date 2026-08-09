"""add interviews

Revision ID: c104d870d14c
Revises: e3f38b83602a
Create Date: 2026-08-09 17:41:12.884210

Hand-edited: autogenerate declares the enums inline, which leaves nothing to
drop on downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c104d870d14c"
down_revision: str | None = "e3f38b83602a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


interview_round = postgresql.ENUM(
    "phone_screen",
    "technical",
    "take_home",
    "system_design",
    "hr",
    "managerial",
    "final",
    "other",
    name="interview_round",
    create_type=False,
)
interview_mode = postgresql.ENUM(
    "onsite", "video", "phone", name="interview_mode", create_type=False
)
interview_outcome = postgresql.ENUM(
    "pending", "passed", "failed", "cancelled", name="interview_outcome", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    interview_round.create(bind, checkfirst=True)
    interview_mode.create(bind, checkfirst=True)
    interview_outcome.create(bind, checkfirst=True)

    op.create_table(
        "interviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("round", interview_round, nullable=False),
        sa.Column("mode", interview_mode, nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("interviewer", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("outcome", interview_outcome, nullable=False),
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
    )
    op.create_index(op.f("ix_interviews_application_id"), "interviews", ["application_id"])
    op.create_index(op.f("ix_interviews_user_id"), "interviews", ["user_id"])
    op.create_index("ix_interviews_user_scheduled", "interviews", ["user_id", "scheduled_at"])
    op.create_index("ix_interviews_user_outcome", "interviews", ["user_id", "outcome"])


def downgrade() -> None:
    op.drop_index("ix_interviews_user_outcome", table_name="interviews")
    op.drop_index("ix_interviews_user_scheduled", table_name="interviews")
    op.drop_index(op.f("ix_interviews_user_id"), table_name="interviews")
    op.drop_index(op.f("ix_interviews_application_id"), table_name="interviews")
    op.drop_table("interviews")

    bind = op.get_bind()
    interview_outcome.drop(bind, checkfirst=True)
    interview_mode.drop(bind, checkfirst=True)
    interview_round.drop(bind, checkfirst=True)
