"""Resume endpoints."""

import uuid
from datetime import timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi import status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional, get_storage
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import Storage
from app.models.user import User
from app.schemas.resume import (
    ResumeDetailResponse,
    ResumeResponse,
    ResumeTextResponse,
    ResumeUpdate,
    ResumeUploadResponse,
    ResumeUsageResponse,
)
from app.services.rate_events import DurableLimiter, TooManyAttempts, upload_bucket
from app.services.resume import (
    InvalidResumeFile,
    ResumeNotFound,
    ResumeService,
    ResumeStorageUnavailable,
    StorageQuotaExceeded,
)

router = APIRouter()

_NOT_FOUND = HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Resume not found")


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The stored file could not be read. Please upload it again.",
    )


def get_resume_service(
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> ResumeService:
    """Storage arrives as a dependency so tests can point it at a temp directory."""
    return ResumeService(db, storage)


@router.get("/limits", summary="Upload limits")
def get_upload_limits(
    current_user: User | None = Depends(get_current_user_optional),
    service: ResumeService = Depends(get_resume_service),
) -> dict[str, object]:
    """Lets the client reject a file before sending it rather than after.

    Declared above /{resume_id} — a literal path registered after a parameterised
    one of the same shape is never reached.

    Auth is optional rather than required. The file rules are the same for
    everyone, and demanding a token to read them would turn a public endpoint
    private — breaking every existing caller to add a field. Signed in, the
    answer also includes what this account has used.
    """
    limits: dict[str, object] = {
        "max_size_bytes": settings.max_upload_bytes,
        "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "allowed_types": settings.allowed_upload_types_list,
        "storage_limit_bytes": settings.max_storage_per_user_bytes,
    }

    if current_user is not None:
        # So the client can say "this will not fit" before spending a minute
        # uploading something that is going to be refused.
        used = service.storage_used(current_user.id)
        limits["storage_used_bytes"] = used
        limits["storage_remaining_bytes"] = max(0, settings.max_storage_per_user_bytes - used)

    return limits


@router.get("", response_model=list[ResumeResponse], summary="List resumes")
def list_resumes(
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> list[ResumeResponse]:
    """Current version of each resume. Older ones come from /{id}/versions."""
    return [ResumeResponse.model_validate(r) for r in service.list_current(current_user.id)]


@router.post(
    "",
    response_model=ResumeUploadResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Upload a resume",
)
def upload_resume(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    replaces_id: uuid.UUID | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    """Pass replaces_id to add a version to an existing resume rather than
    creating a new one."""
    # Counted per account and kept in the database, because the thing being
    # protected — a 500 MB shared database — does not get bigger when the
    # process restarts.
    limits = DurableLimiter(db)
    bucket = upload_bucket(current_user.id)
    window = timedelta(hours=1)
    try:
        limits.check(bucket, limit=settings.UPLOAD_HOURLY_LIMIT, window=window)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many uploads in the last hour. Try again shortly.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    try:
        result = service.upload(
            current_user.id,
            source=file.file,
            filename=file.filename or "resume.pdf",
            content_type=file.content_type,
            title=title,
            notes=notes,
            replaces_id=replaces_id,
        )
    except InvalidResumeFile as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except StorageQuotaExceeded as exc:
        # 413 rather than 422: nothing is wrong with the file, it is the size
        # that cannot be accepted, and the message says what to do about it.
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
    except ResumeStorageUnavailable as exc:
        raise _unavailable() from exc

    # Only a stored file counts against the allowance. Recording a rejected
    # upload would let a loop of invalid files exhaust the caller's own quota.
    limits.record(bucket, window=window)

    response = ResumeUploadResponse.model_validate(result.resume)
    if result.duplicate_of is not None:
        response.duplicate_of_id = result.duplicate_of.id
        response.duplicate_of_title = result.duplicate_of.title
    return response


@router.get("/{resume_id}", response_model=ResumeDetailResponse, summary="Get one resume")
def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeDetailResponse:
    try:
        resume = service.get(current_user.id, resume_id)
        versions = service.list_versions(current_user.id, resume_id)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc

    response = ResumeDetailResponse.model_validate(resume)
    response.versions = [ResumeResponse.model_validate(v) for v in versions]
    return response


@router.get("/{resume_id}/versions", response_model=list[ResumeResponse], summary="Version history")
def list_versions(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> list[ResumeResponse]:
    try:
        versions = service.list_versions(current_user.id, resume_id)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
    return [ResumeResponse.model_validate(v) for v in versions]


@router.get("/{resume_id}/text", response_model=ResumeTextResponse, summary="Extracted text")
def get_resume_text(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeTextResponse:
    """Separate from the detail view because the text is large and most views
    never show it."""
    try:
        resume = service.get(current_user.id, resume_id)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
    return ResumeTextResponse.model_validate(resume)


@router.get("/{resume_id}/download", summary="Download the file")
def download_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> StreamingResponse:
    try:
        resume, stream = service.open_file(current_user.id, resume_id)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
    except ResumeStorageUnavailable as exc:
        raise _unavailable() from exc

    # RFC 5987: the quoted name stays ASCII for older clients, filename* carries
    # the real one for everything else.
    disposition = (
        f"inline; filename=\"resume.pdf\"; filename*=UTF-8''{quote(resume.original_filename)}"
    )

    return StreamingResponse(
        stream,
        media_type=resume.content_type,
        headers={
            "Content-Disposition": disposition,
            "Content-Length": str(resume.size_bytes),
        },
    )


@router.get(
    "/{resume_id}/usage",
    response_model=ResumeUsageResponse,
    summary="How many applications use this",
)
def get_resume_usage(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeUsageResponse:
    """Shown before deleting, so the consequence is visible first."""
    try:
        count = service.usage_count(current_user.id, resume_id)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
    return ResumeUsageResponse(application_count=count)


@router.patch("/{resume_id}", response_model=ResumeResponse, summary="Update resume details")
def update_resume(
    resume_id: uuid.UUID,
    payload: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    try:
        resume = service.update(current_user.id, resume_id, payload)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
    return ResumeResponse.model_validate(resume)


@router.post(
    "/{resume_id}/set-current",
    response_model=ResumeResponse,
    summary="Make this the current version",
)
def set_current_version(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    try:
        resume = service.set_current(current_user.id, resume_id)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
    return ResumeResponse.model_validate(resume)


@router.delete(
    "/{resume_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Delete a resume version",
)
def delete_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
) -> None:
    try:
        service.delete(current_user.id, resume_id)
    except ResumeNotFound as exc:
        raise _NOT_FOUND from exc
