"""Data access for interviews.

Same rule as the rest: every method takes user_id and filters on it.
"""

import uuid
from datetime import datetime

from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import (
    CLOSED_STATUSES,
    SETTLED_OUTCOMES,
    ApplicationStatus,
    InterviewOutcome,
)
from app.models.interview import Interview


class InterviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- reads ----

    def get(self, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview | None:
        return self.db.execute(
            select(Interview).where(
                Interview.id == interview_id,
                Interview.user_id == user_id,
            )
        ).scalar_one_or_none()

    def list_for_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[Interview]:
        return list(
            self.db.execute(
                select(Interview)
                .where(
                    Interview.user_id == user_id,
                    Interview.application_id == application_id,
                )
                .order_by(Interview.scheduled_at)
            )
            .scalars()
            .all()
        )

    def _with_application(
        self, user_id: uuid.UUID
    ) -> Select[tuple[Interview, str, str, ApplicationStatus]]:
        """Interview rows joined to the few application columns a list needs."""
        return (
            select(
                Interview,
                Application.company_name,
                Application.job_title,
                Application.status,
            )
            .join(Application, Application.id == Interview.application_id)
            .where(Interview.user_id == user_id)
        )

    def upcoming(
        self, user_id: uuid.UUID, *, now: datetime, until: datetime | None = None, limit: int = 20
    ) -> list[Row]:
        stmt = self._with_application(user_id).where(
            Interview.scheduled_at >= now,
            Interview.outcome.notin_(list(SETTLED_OUTCOMES)),
        )
        if until is not None:
            stmt = stmt.where(Interview.scheduled_at <= until)

        return list(self.db.execute(stmt.order_by(Interview.scheduled_at).limit(limit)).all())

    def awaiting_outcome(self, user_id: uuid.UUID, *, now: datetime) -> list[Row]:
        """Happened, but nobody recorded how it went."""
        return list(
            self.db.execute(
                self._with_application(user_id)
                .where(
                    Interview.scheduled_at < now,
                    Interview.outcome == InterviewOutcome.PENDING,
                )
                .order_by(Interview.scheduled_at.desc())
            ).all()
        )

    def stale_applications(self, user_id: uuid.UUID, *, before: datetime) -> list[Application]:
        """Still open, but nothing has happened for a while.

        Ordered by updated_at, which moves whenever anything about the
        application changes — so editing a note counts as activity, not just a
        stage change.
        """
        return list(
            self.db.execute(
                select(Application)
                .where(
                    Application.user_id == user_id,
                    Application.status.notin_(list(CLOSED_STATUSES)),
                    # A wishlist entry going quiet is not news — nothing was sent.
                    Application.status != ApplicationStatus.WISHLIST,
                    Application.updated_at < before,
                )
                .order_by(Application.updated_at)
            )
            .scalars()
            .all()
        )

    def count_for_application(self, user_id: uuid.UUID, application_id: uuid.UUID) -> int:
        count: int = self.db.execute(
            select(func.count())
            .select_from(Interview)
            .where(
                Interview.user_id == user_id,
                Interview.application_id == application_id,
            )
        ).scalar_one()
        return count

    # ---- writes ----

    def add(self, interview: Interview) -> Interview:
        self.db.add(interview)
        self.db.flush()
        return interview

    def delete(self, interview: Interview) -> None:
        self.db.delete(interview)
        self.db.flush()
