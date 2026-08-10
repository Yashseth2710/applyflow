"""Interview and reminder endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewUpdate,
    InterviewWithApplication,
    ReminderList,
)
from app.services.interview import (
    ApplicationNotFound,
    InterviewNotFound,
    InterviewService,
    TooManyInterviews,
)

router = APIRouter()

_NOT_FOUND = HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Interview not found")
_NO_APPLICATION = HTTPException(
    status_code=http_status.HTTP_404_NOT_FOUND, detail="Application not found"
)


@router.get(
    "/upcoming",
    response_model=list[InterviewWithApplication],
    summary="Interviews coming up",
)
def list_upcoming(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InterviewWithApplication]:
    """Declared above /{interview_id} so the literal path is reachable."""
    rows = InterviewService(db).upcoming(current_user.id, limit=limit)
    return [_with_application(row) for row in rows]


@router.get("/reminders", response_model=ReminderList, summary="Things needing attention")
def list_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderList:
    """Derived from interviews and application dates on each request — there is
    no reminders table and nothing to keep in sync."""
    items = InterviewService(db).reminders(current_user.id)
    return ReminderList(items=items, total=len(items))


@router.get(
    "",
    response_model=list[InterviewResponse],
    summary="Interviews for one application",
)
def list_for_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InterviewResponse]:
    try:
        interviews = InterviewService(db).list_for_application(current_user.id, application_id)
    except ApplicationNotFound as exc:
        raise _NO_APPLICATION from exc
    return [InterviewResponse.model_validate(i) for i in interviews]


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Schedule an interview",
)
def create_interview(
    payload: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    try:
        interview = InterviewService(db).create(current_user.id, payload)
    except ApplicationNotFound as exc:
        raise _NO_APPLICATION from exc
    except TooManyInterviews as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return InterviewResponse.model_validate(interview)


@router.get("/{interview_id}", response_model=InterviewResponse, summary="Get one interview")
def get_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    try:
        interview = InterviewService(db).get(current_user.id, interview_id)
    except InterviewNotFound as exc:
        raise _NOT_FOUND from exc
    return InterviewResponse.model_validate(interview)


@router.patch("/{interview_id}", response_model=InterviewResponse, summary="Update an interview")
def update_interview(
    interview_id: uuid.UUID,
    payload: InterviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewResponse:
    try:
        interview = InterviewService(db).update(current_user.id, interview_id, payload)
    except InterviewNotFound as exc:
        raise _NOT_FOUND from exc
    return InterviewResponse.model_validate(interview)


@router.delete(
    "/{interview_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Delete an interview",
)
def delete_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        InterviewService(db).delete(current_user.id, interview_id)
    except InterviewNotFound as exc:
        raise _NOT_FOUND from exc


def _with_application(row: tuple) -> InterviewWithApplication:
    interview, company_name, job_title, status = row
    return InterviewWithApplication(
        **InterviewResponse.model_validate(interview).model_dump(),
        company_name=company_name,
        job_title=job_title,
        application_status=status,
    )
