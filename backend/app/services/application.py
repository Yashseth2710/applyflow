"""Application business logic.

Knows nothing about HTTP; raises domain errors the API layer maps to statuses.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.repositories.application import ApplicationRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    SortField,
    SortOrder,
)


class ApplicationNotFound(Exception):
    """Raised when the application does not exist *or* belongs to someone else.

    Deliberately one error for both. Distinguishing them would confirm that an
    id exists, letting an attacker enumerate other users' records.
    """


#: Statuses that imply the application was actually submitted.
_SUBMITTED = frozenset(ApplicationStatus) - {ApplicationStatus.WISHLIST}


class ApplicationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ApplicationRepository(db)

    def create(self, user_id: uuid.UUID, payload: ApplicationCreate) -> Application:
        data = payload.model_dump()
        status = data.pop("status")

        application = Application(
            user_id=user_id,
            status=status,
            position=self.repo.next_position(user_id, status),
            **data,
        )

        # Moving straight to "applied" without a date is the common case — the
        # user is recording something they just did. Stamping it here means the
        # analytics milestone isn't full of nulls.
        if application.date_applied is None and status in _SUBMITTED:
            application.date_applied = datetime.now(UTC)

        self.repo.add(application)
        # First history entry has from_status=None, recording what it started as.
        self.repo.record_status_change(application, from_status=None, to_status=status)

        self.db.commit()
        self.db.refresh(application)
        return application

    def get(self, user_id: uuid.UUID, application_id: uuid.UUID) -> Application:
        application = self.repo.get_with_history(user_id, application_id)
        if application is None:
            raise ApplicationNotFound
        return application

    # See the note in ApplicationRepository: a method named `list` shadows the
    # builtin for every annotation defined after it in the class body.
    def paginate(
        self,
        user_id: uuid.UUID,
        *,
        status: ApplicationStatus | None = None,
        search: str | None = None,
        source: str | None = None,
        work_mode: str | None = None,
        sort_by: SortField = "created_at",
        order: SortOrder = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Application], int]:
        return self.repo.paginate(
            user_id,
            status=status,
            search=search,
            source=source,
            work_mode=work_mode,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )

    def board(self, user_id: uuid.UUID) -> list[Application]:
        return self.repo.list_for_board(user_id)

    def update(
        self, user_id: uuid.UUID, application_id: uuid.UUID, payload: ApplicationUpdate
    ) -> Application:
        application = self.repo.get(user_id, application_id)
        if application is None:
            raise ApplicationNotFound

        # exclude_unset so PATCH only touches supplied fields. Without it,
        # every omitted field would be overwritten with None.
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(application, field, value)

        self.db.commit()
        self.db.refresh(application)
        return application

    def change_status(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        *,
        status: ApplicationStatus,
        position: int | None = None,
    ) -> Application:
        application = self.repo.get(user_id, application_id)
        if application is None:
            raise ApplicationNotFound

        previous = application.status
        application.status = status
        application.position = (
            position if position is not None else self.repo.next_position(user_id, status)
        )

        if application.date_applied is None and status in _SUBMITTED:
            application.date_applied = datetime.now(UTC)

        # Only log real transitions. A drag that lands a card back in its own
        # column would otherwise pollute the history and skew time-in-stage.
        if previous != status:
            self.repo.record_status_change(application, from_status=previous, to_status=status)

        self.db.commit()
        self.db.refresh(application)
        return application

    def delete(self, user_id: uuid.UUID, application_id: uuid.UUID) -> None:
        application = self.repo.get(user_id, application_id)
        if application is None:
            raise ApplicationNotFound

        self.repo.delete(application)
        self.db.commit()

    def sources(self, user_id: uuid.UUID) -> list[str]:
        return self.repo.distinct_sources(user_id)
