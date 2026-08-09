"""Application endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import ApplicationStatus, WorkMode
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicationUpdate,
    BoardColumn,
    BoardResponse,
    Page,
    SortField,
    SortOrder,
)
from app.services.application import ApplicationNotFound, ApplicationService

router = APIRouter()

# Returned for both "no such application" and "belongs to another user".
# A 403 on the latter would confirm the id exists — see docs/api-spec.md.
_NOT_FOUND = HTTPException(
    status_code=http_status.HTTP_404_NOT_FOUND, detail="Application not found"
)

#: Column order for the board. Terminal statuses are excluded — they are
#: returned separately so the UI can collapse them. See docs/roadmap.md.
BOARD_COLUMN_ORDER: list[ApplicationStatus] = [
    ApplicationStatus.WISHLIST,
    ApplicationStatus.APPLIED,
    ApplicationStatus.ASSESSMENT,
    ApplicationStatus.PHONE_SCREEN,
    ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationStatus.HR_INTERVIEW,
    ApplicationStatus.FINAL_INTERVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.ACCEPTED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.ON_HOLD,
]


@router.get("", response_model=Page[ApplicationResponse], summary="List applications")
def list_applications(
    status: ApplicationStatus | None = None,
    search: str | None = Query(default=None, max_length=200),
    source: str | None = Query(default=None, max_length=100),
    work_mode: WorkMode | None = None,
    sort_by: SortField = "created_at",
    order: SortOrder = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ApplicationResponse]:
    items, total = ApplicationService(db).paginate(
        current_user.id,
        status=status,
        search=search,
        source=source,
        work_mode=work_mode.value if work_mode else None,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    return Page[ApplicationResponse](
        items=[ApplicationResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/board", response_model=BoardResponse, summary="Applications by stage")
def get_board(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BoardResponse:
    """Grouped in one query rather than one request per column.

    Every status is returned, including terminal ones — the frontend decides
    which to show as columns and which to collapse.
    """
    applications = ApplicationService(db).board(current_user.id)

    grouped: dict[ApplicationStatus, list[ApplicationResponse]] = {
        s: [] for s in BOARD_COLUMN_ORDER
    }
    for app_row in applications:
        grouped[app_row.status].append(ApplicationResponse.model_validate(app_row))

    return BoardResponse(
        columns=[
            BoardColumn(status=s, count=len(grouped[s]), items=grouped[s])
            for s in BOARD_COLUMN_ORDER
        ],
        total=len(applications),
    )


@router.get("/sources", response_model=list[str], summary="Sources used so far")
def list_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[str]:
    """Powers the source filter dropdown without a fixed enum."""
    return ApplicationService(db).sources(current_user.id)


@router.post(
    "",
    response_model=ApplicationDetailResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create an application",
)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationDetailResponse:
    application = ApplicationService(db).create(current_user.id, payload)
    return ApplicationDetailResponse.model_validate(application)


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Get one application",
)
def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationDetailResponse:
    try:
        application = ApplicationService(db).get(current_user.id, application_id)
    except ApplicationNotFound as exc:
        raise _NOT_FOUND from exc
    return ApplicationDetailResponse.model_validate(application)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update an application",
)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    try:
        application = ApplicationService(db).update(current_user.id, application_id, payload)
    except ApplicationNotFound as exc:
        raise _NOT_FOUND from exc
    return ApplicationResponse.model_validate(application)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    summary="Move to another stage",
)
def change_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    """Separate from PATCH /{id} so every stage change is written to history."""
    try:
        application = ApplicationService(db).change_status(
            current_user.id,
            application_id,
            status=payload.status,
            position=payload.position,
        )
    except ApplicationNotFound as exc:
        raise _NOT_FOUND from exc
    return ApplicationResponse.model_validate(application)


@router.delete(
    "/{application_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Delete an application",
)
def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        ApplicationService(db).delete(current_user.id, application_id)
    except ApplicationNotFound as exc:
        raise _NOT_FOUND from exc
