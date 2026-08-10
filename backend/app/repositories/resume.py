"""Data access for resumes.

Same rule as applications: every method takes user_id and filters on it, so an
endpoint cannot forget the owner check.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.resume import Resume


class ResumeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- reads ----

    def get(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume | None:
        return self.db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        ).scalar_one_or_none()

    def list_current(self, user_id: uuid.UUID) -> list[Resume]:
        """One row per family — the version the user last marked current."""
        return list(
            self.db.execute(
                select(Resume)
                .where(Resume.user_id == user_id, Resume.is_current.is_(True))
                .order_by(Resume.created_at.desc())
            )
            .scalars()
            .all()
        )

    def list_versions(self, user_id: uuid.UUID, family_id: uuid.UUID) -> list[Resume]:
        return list(
            self.db.execute(
                select(Resume)
                .where(Resume.user_id == user_id, Resume.family_id == family_id)
                .order_by(Resume.version.desc())
            )
            .scalars()
            .all()
        )

    def next_version(self, user_id: uuid.UUID, family_id: uuid.UUID) -> int:
        current_max = self.db.execute(
            select(func.max(Resume.version)).where(
                Resume.user_id == user_id, Resume.family_id == family_id
            )
        ).scalar()
        return 1 if current_max is None else current_max + 1

    def find_duplicate(self, user_id: uuid.UUID, content_hash: str) -> Resume | None:
        """An identical file already uploaded, if any. Used to warn, not to block —
        uploading the same PDF under two titles is a legitimate thing to do."""
        return self.db.execute(
            select(Resume)
            .where(Resume.user_id == user_id, Resume.content_hash == content_hash)
            .order_by(Resume.created_at)
            .limit(1)
        ).scalar_one_or_none()

    def total_bytes(self, user_id: uuid.UUID) -> int:
        """How much this account is holding, versions included.

        Counted from the resume rows rather than the stored bytes so the answer
        is the same whichever storage backend is configured — and every version
        is a real file, so old ones count against the quota exactly like the
        current one does.
        """
        return (
            self.db.execute(
                select(func.coalesce(func.sum(Resume.size_bytes), 0)).where(
                    Resume.user_id == user_id
                )
            ).scalar_one()
            or 0
        )

    def count_applications_using(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> int:
        return self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user_id, Application.resume_id == resume_id)
        ).scalar_one()

    # ---- writes ----

    def add(self, resume: Resume) -> Resume:
        self.db.add(resume)
        self.db.flush()
        return resume

    def delete(self, resume: Resume) -> None:
        self.db.delete(resume)
        self.db.flush()

    def clear_current_flag(self, user_id: uuid.UUID, family_id: uuid.UUID) -> None:
        self.db.execute(
            update(Resume)
            .where(
                Resume.user_id == user_id,
                Resume.family_id == family_id,
                Resume.is_current.is_(True),
            )
            .values(is_current=False)
        )
        self.db.flush()
