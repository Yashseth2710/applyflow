"""Resume business logic: upload, versioning, text extraction, deletion.

No HTTP here — the API layer maps these errors to status codes.
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import IO

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import Storage, StorageError, build_key, build_storage
from app.models.enums import ExtractionStatus
from app.models.resume import Resume
from app.repositories.resume import ResumeRepository
from app.schemas.resume import ResumeUpdate
from app.services.extraction import extract_pdf_text

logger = logging.getLogger(__name__)

#: Files bigger than this spill from memory to a temp file while we hash them.
_SPOOL_THRESHOLD = 1024 * 1024

#: Every allowed type, and the bytes a real file of that type starts with.
#: Extensions and the browser-supplied content type are both trivially faked;
#: this is the check that actually means something.
_MAGIC_BYTES: dict[str, bytes] = {"application/pdf": b"%PDF-"}


class ResumeNotFound(Exception):
    """Doesn't exist, or belongs to someone else."""


class InvalidResumeFile(Exception):
    """Rejected before anything was stored."""


class ResumeStorageUnavailable(Exception):
    """The file could not be written or read back."""


@dataclass(frozen=True)
class UploadResult:
    resume: Resume
    #: An earlier upload of byte-identical content, if there is one. The API
    #: passes this back as a warning; it never blocks the upload.
    duplicate_of: Resume | None = None


class ResumeService:
    def __init__(self, db: Session, storage: Storage | None = None) -> None:
        self.db = db
        self.repo = ResumeRepository(db)
        self.storage = storage or build_storage(db)

    # ---- reads ----

    def get(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
        resume = self.repo.get(user_id, resume_id)
        if resume is None:
            raise ResumeNotFound
        return resume

    def list_current(self, user_id: uuid.UUID) -> list[Resume]:
        return self.repo.list_current(user_id)

    def list_versions(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> list[Resume]:
        resume = self.get(user_id, resume_id)
        return self.repo.list_versions(user_id, resume.family_id)

    def open_file(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> tuple[Resume, IO[bytes]]:
        resume = self.get(user_id, resume_id)
        try:
            return resume, self.storage.open(resume.storage_key)
        except StorageError as exc:
            # The row exists but the bytes don't — a wiped ephemeral disk, most
            # likely. Worth logging loudly; it means storage was misconfigured.
            logger.error("Missing stored file for resume %s: %s", resume.id, exc)
            raise ResumeStorageUnavailable(str(exc)) from exc

    # ---- upload ----

    def upload(
        self,
        user_id: uuid.UUID,
        *,
        source: IO[bytes],
        filename: str,
        content_type: str | None,
        title: str | None = None,
        notes: str | None = None,
        replaces_id: uuid.UUID | None = None,
    ) -> UploadResult:
        """Store a file and record it.

        replaces_id makes this a new version of an existing resume rather than a
        new one; the previous version is kept and stops being current.
        """
        buffered, size, digest = self._buffer_and_hash(source)

        try:
            resolved_type = self._validate(buffered, filename, content_type, size)

            family_id, version, previous = self._resolve_family(user_id, replaces_id)

            resume = Resume(
                id=uuid.uuid4(),
                user_id=user_id,
                family_id=family_id,
                version=version,
                is_current=True,
                title=(title or (previous.title if previous else None) or _title_from(filename)),
                notes=notes,
                original_filename=Path(filename).name[:255],
                content_type=resolved_type,
                size_bytes=size,
                content_hash=digest,
                storage_key="",
                extraction_status=ExtractionStatus.PENDING,
            )
            resume.storage_key = build_key(user_id, resume.id, filename)

            buffered.seek(0)
            result = extract_pdf_text(buffered)
            resume.extraction_status = result.status
            resume.extracted_text = result.text
            resume.extraction_error = result.error

            buffered.seek(0)
            try:
                self.storage.save(resume.storage_key, buffered, owner_id=user_id)
            except StorageError as exc:
                logger.exception("Could not write resume file")
                raise ResumeStorageUnavailable(str(exc)) from exc

            duplicate = self.repo.find_duplicate(user_id, digest)

            if previous is not None:
                self.repo.clear_current_flag(user_id, family_id)

            self.repo.add(resume)

            try:
                self.db.commit()
            except Exception:
                # Don't leave an orphaned file behind when the row didn't land.
                self.db.rollback()
                self.storage.delete(resume.storage_key)
                raise

            self.db.refresh(resume)
            return UploadResult(resume=resume, duplicate_of=duplicate)

        finally:
            buffered.close()

    def _buffer_and_hash(self, source: IO[bytes]) -> tuple[SpooledTemporaryFile[bytes], int, str]:
        """Read the upload once, capping the size as we go.

        Streaming rather than trusting a Content-Length header: the header is
        client-supplied, and reading first to check the size afterwards is how
        you get memory-exhausted by a large upload.
        """
        limit = settings.max_upload_bytes
        # Not a context manager: the buffer outlives this function and is closed
        # by upload()'s finally block.
        buffered: SpooledTemporaryFile[bytes] = SpooledTemporaryFile(  # noqa: SIM115
            max_size=_SPOOL_THRESHOLD
        )
        hasher = hashlib.sha256()
        size = 0

        try:
            while chunk := source.read(64 * 1024):
                size += len(chunk)
                if size > limit:
                    raise InvalidResumeFile(
                        f"File is larger than the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
                    )
                hasher.update(chunk)
                buffered.write(chunk)
        except Exception:
            buffered.close()
            raise

        buffered.seek(0)
        return buffered, size, hasher.hexdigest()

    def _validate(
        self, buffered: IO[bytes], filename: str, content_type: str | None, size: int
    ) -> str:
        if size == 0:
            raise InvalidResumeFile("File is empty.")

        allowed = settings.allowed_upload_types_list
        declared = (content_type or "").split(";")[0].strip().lower()

        if declared not in allowed:
            pretty = ", ".join(t.split("/")[-1].upper() for t in allowed)
            raise InvalidResumeFile(f"Only {pretty} files are accepted.")

        magic = _MAGIC_BYTES.get(declared)
        if magic is not None:
            buffered.seek(0)
            if not buffered.read(len(magic)).startswith(magic):
                raise InvalidResumeFile(
                    f"This file is named like a {declared.split('/')[-1].upper()} "
                    "but its contents are not one."
                )
            buffered.seek(0)

        if not Path(filename).name.strip():
            raise InvalidResumeFile("File has no name.")

        return declared

    def _resolve_family(
        self, user_id: uuid.UUID, replaces_id: uuid.UUID | None
    ) -> tuple[uuid.UUID, int, Resume | None]:
        if replaces_id is None:
            # First version of a new resume: the family is named after it, so
            # there is no parent row whose deletion would orphan the rest.
            new_family = uuid.uuid4()
            return new_family, 1, None

        previous = self.repo.get(user_id, replaces_id)
        if previous is None:
            raise ResumeNotFound

        version = self.repo.next_version(user_id, previous.family_id)
        return previous.family_id, version, previous

    # ---- writes ----

    def update(self, user_id: uuid.UUID, resume_id: uuid.UUID, payload: ResumeUpdate) -> Resume:
        resume = self.get(user_id, resume_id)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(resume, field, value)

        self.db.commit()
        self.db.refresh(resume)
        return resume

    def set_current(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
        """Make an older version the active one again."""
        resume = self.get(user_id, resume_id)

        self.repo.clear_current_flag(user_id, resume.family_id)
        resume.is_current = True

        self.db.commit()
        self.db.refresh(resume)
        return resume

    def usage_count(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> int:
        self.get(user_id, resume_id)
        return self.repo.count_applications_using(user_id, resume_id)

    def delete(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> None:
        """Delete one version. Applications that used it keep their record and
        lose the link, via ON DELETE SET NULL."""
        resume = self.get(user_id, resume_id)
        family_id = resume.family_id
        was_current = resume.is_current
        storage_key = resume.storage_key

        self.repo.delete(resume)

        if was_current:
            remaining = self.repo.list_versions(user_id, family_id)
            if remaining:
                # Ordered newest version first, so this is the latest survivor.
                remaining[0].is_current = True

        # Before the commit, not after. The database backend runs in this very
        # session, so a delete issued after committing would open a second
        # transaction that nothing ever commits, and the bytes would survive the
        # row that described them.
        try:
            self.storage.delete(storage_key)
        except StorageError:
            logger.warning("Could not remove stored file %s", storage_key)

        self.db.commit()


def _title_from(filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return (stem or "Resume")[:200]
