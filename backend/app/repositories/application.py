"""Data access for applications.

Every method takes `user_id` and filters on it. There is deliberately no
"get by id" that skips the owner check — an endpoint cannot forget a filter
this layer will not let it omit.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.application import Application, ApplicationStatusHistory
from app.models.enums import ApplicationStatus
from app.schemas.application import SortField, SortOrder

_SORT_COLUMNS = {
    "created_at": Application.created_at,
    "updated_at": Application.updated_at,
    "date_applied": Application.date_applied,
    "company_name": Application.company_name,
    "job_title": Application.job_title,
}


class ApplicationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- reads ----

    def get(self, user_id: uuid.UUID, application_id: uuid.UUID) -> Application | None:
        return self.db.execute(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
        ).scalar_one_or_none()

    def get_with_history(self, user_id: uuid.UUID, application_id: uuid.UUID) -> Application | None:
        return self.db.execute(
            select(Application)
            .options(selectinload(Application.status_history))
            .where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
        ).scalar_one_or_none()

    def _filtered(
        self,
        user_id: uuid.UUID,
        *,
        status: ApplicationStatus | None = None,
        statuses: Sequence[ApplicationStatus] | None = None,
        search: str | None = None,
        source: str | None = None,
        work_mode: str | None = None,
    ) -> Select[tuple[Application]]:
        stmt = select(Application).where(Application.user_id == user_id)

        if status is not None:
            stmt = stmt.where(Application.status == status)
        if statuses:
            stmt = stmt.where(Application.status.in_(statuses))
        if source:
            stmt = stmt.where(Application.source == source)
        if work_mode:
            stmt = stmt.where(Application.work_mode == work_mode)
        if search:
            # ILIKE rather than full-text search: users type partial company
            # names ("goog"), which to_tsquery would not match. The dataset is
            # per-user and small, so the index trade-off does not bite.
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Application.company_name.ilike(pattern),
                    Application.job_title.ilike(pattern),
                    Application.location.ilike(pattern),
                )
            )
        return stmt

    # Not named `list`: a method called `list` shadows the builtin inside the
    # class body, so any later `-> list[X]` annotation resolves to the method
    # and raises "'function' object is not subscriptable" at import time.
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
        stmt = self._filtered(
            user_id,
            status=status,
            search=search,
            source=source,
            work_mode=work_mode,
        )

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        column = _SORT_COLUMNS[sort_by]
        # nulls_last matters for date_applied: wishlist rows have no applied
        # date, and without this they would head the list on a descending sort.
        ordering = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()

        rows = (
            self.db.execute(
                stmt.order_by(ordering, Application.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def list_for_board(self, user_id: uuid.UUID) -> list[Application]:
        """Every application, ordered for the Kanban board.

        Unpaginated on purpose: a board with a page 2 is not a board. The realistic
        ceiling is a few hundred rows per user, which is a trivial query.
        """
        return list(
            self.db.execute(
                self._filtered(user_id).order_by(
                    Application.position, Application.created_at.desc()
                )
            )
            .scalars()
            .all()
        )

    def next_position(self, user_id: uuid.UUID, status: ApplicationStatus) -> int:
        """Append to the end of a column. Gaps are fine — position only needs to
        sort correctly, not be contiguous."""
        current_max = self.db.execute(
            select(func.max(Application.position)).where(
                Application.user_id == user_id,
                Application.status == status,
            )
        ).scalar()
        return 0 if current_max is None else current_max + 1

    def distinct_sources(self, user_id: uuid.UUID) -> list[str]:
        rows = (
            self.db.execute(
                select(Application.source)
                .where(Application.user_id == user_id, Application.source.isnot(None))
                .distinct()
                .order_by(Application.source)
            )
            .scalars()
            .all()
        )
        # The isnot(None) filter can't narrow the column's declared `str | None`
        # for the type checker, so drop them explicitly rather than casting.
        return [s for s in rows if s is not None]

    # ---- writes ----

    def add(self, application: Application) -> Application:
        self.db.add(application)
        self.db.flush()
        return application

    def delete(self, application: Application) -> None:
        self.db.delete(application)
        self.db.flush()

    def record_status_change(
        self,
        application: Application,
        *,
        from_status: ApplicationStatus | None,
        to_status: ApplicationStatus,
    ) -> ApplicationStatusHistory:
        entry = ApplicationStatusHistory(
            application_id=application.id,
            user_id=application.user_id,
            from_status=from_status,
            to_status=to_status,
            changed_at=datetime.now(UTC),
        )
        self.db.add(entry)
        self.db.flush()
        return entry
