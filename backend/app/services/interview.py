"""Interview business logic, and the reminders derived from it."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import InterviewRound
from app.models.interview import Interview
from app.repositories.application import ApplicationRepository
from app.repositories.interview import InterviewRepository
from app.schemas.interview import (
    InterviewCreate,
    InterviewUpdate,
    Reminder,
)

#: How far ahead an interview counts as "coming up".
UPCOMING_WINDOW = timedelta(days=7)

#: How long an open application can go without any change before it's worth a nudge.
STALE_AFTER = timedelta(days=14)

ROUND_LABELS = {
    "phone_screen": "Phone screen",
    "technical": "Technical",
    "take_home": "Take-home",
    "system_design": "System design",
    "hr": "HR",
    "managerial": "Managerial",
    "final": "Final round",
    "other": "Interview",
}


class InterviewNotFound(Exception):
    """Doesn't exist, or belongs to someone else."""


class ApplicationNotFound(Exception):
    """The application an interview was going to hang off doesn't exist."""


class TooManyInterviews(Exception):
    """This application already has as many as it is allowed."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"An application can hold at most {limit} interviews.")
        self.limit = limit


class InterviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = InterviewRepository(db)
        self.applications = ApplicationRepository(db)

    # ---- reads ----

    def get(self, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
        interview = self.repo.get(user_id, interview_id)
        if interview is None:
            raise InterviewNotFound
        return interview

    def list_for_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[Interview]:
        # Prove the application is the caller's before listing anything under it.
        if self.applications.get(user_id, application_id) is None:
            raise ApplicationNotFound
        return self.repo.list_for_application(user_id, application_id)

    def upcoming(self, user_id: uuid.UUID, *, limit: int = 20) -> list[tuple]:
        return [tuple(row) for row in self.repo.upcoming(user_id, now=_now(), limit=limit)]

    # ---- writes ----

    def create(self, user_id: uuid.UUID, payload: InterviewCreate) -> Interview:
        application = self.applications.get(user_id, payload.application_id)
        if application is None:
            raise ApplicationNotFound

        # A stage can hold several interviews. It cannot hold fifty, and these
        # rows are otherwise an unbounded way to grow the database.
        if (
            self.repo.count_for_application(user_id, application.id)
            >= settings.MAX_INTERVIEWS_PER_APPLICATION
        ):
            raise TooManyInterviews(settings.MAX_INTERVIEWS_PER_APPLICATION)

        data = payload.model_dump()
        data.pop("application_id")

        interview = Interview(
            user_id=user_id,
            application_id=application.id,
            **data,
        )
        self.repo.add(interview)
        self.db.commit()
        self.db.refresh(interview)
        return interview

    def update(
        self, user_id: uuid.UUID, interview_id: uuid.UUID, payload: InterviewUpdate
    ) -> Interview:
        interview = self.get(user_id, interview_id)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(interview, field, value)

        self.db.commit()
        self.db.refresh(interview)
        return interview

    def delete(self, user_id: uuid.UUID, interview_id: uuid.UUID) -> None:
        interview = self.get(user_id, interview_id)
        self.repo.delete(interview)
        self.db.commit()

    # ---- reminders ----

    def reminders(self, user_id: uuid.UUID) -> list[Reminder]:
        """Everything worth a nudge, most urgent first.

        Worked out on each request. Nothing is stored, so a reminder cannot
        survive the thing that caused it.
        """
        now = _now()
        items: list[Reminder] = []

        for row in self.repo.upcoming(user_id, now=now, until=now + UPCOMING_WINDOW, limit=50):
            interview, company, title, _status = row
            items.append(
                Reminder(
                    kind="interview_upcoming",
                    severity="info",
                    title=f"{_round_label(interview.round)} at {company}",
                    detail=f"{title} — {_describe_when(interview.scheduled_at, now)}",
                    application_id=interview.application_id,
                    interview_id=interview.id,
                    occurs_at=interview.scheduled_at,
                )
            )

        for row in self.repo.awaiting_outcome(user_id, now=now):
            interview, company, title, _status = row
            items.append(
                Reminder(
                    kind="interview_needs_outcome",
                    severity="warning",
                    title=f"How did {company} go?",
                    detail=(
                        f"{_round_label(interview.round)} for {title} was "
                        f"{_describe_when(interview.scheduled_at, now)}. Record the outcome."
                    ),
                    application_id=interview.application_id,
                    interview_id=interview.id,
                    occurs_at=interview.scheduled_at,
                )
            )

        for application in self.repo.stale_applications(user_id, before=now - STALE_AFTER):
            days = max(1, (now - application.updated_at).days)
            items.append(
                Reminder(
                    kind="application_stale",
                    severity="warning",
                    title=f"No movement on {application.company_name}",
                    detail=(
                        f"{application.job_title} hasn't changed in {days} days. Worth a follow-up."
                    ),
                    application_id=application.id,
                    occurs_at=application.updated_at,
                )
            )

        # Overdue things first, then the soonest upcoming. Sorting by distance
        # from now puts "yesterday" above "next week" without special cases.
        items.sort(
            key=lambda r: (r.severity != "warning", abs((r.occurs_at - now).total_seconds()))
        )
        return items


def _now() -> datetime:
    return datetime.now(UTC)


def _round_label(round_: InterviewRound | str) -> str:
    value = round_.value if isinstance(round_, InterviewRound) else str(round_)
    return ROUND_LABELS.get(value, "Interview")


def _describe_when(moment: datetime, now: datetime) -> str:
    """Plain wording, since these are read at a glance."""
    delta = moment - now
    days = round(delta.total_seconds() / 86400)

    if delta.total_seconds() < 0:
        past_days = abs(days)
        if past_days == 0:
            return "earlier today"
        if past_days == 1:
            return "yesterday"
        return f"{past_days} days ago"

    if days == 0:
        hours = max(1, round(delta.total_seconds() / 3600))
        return "in about an hour" if hours == 1 else f"in about {hours} hours"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"
