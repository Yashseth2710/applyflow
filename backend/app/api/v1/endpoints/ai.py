"""AI endpoints."""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.api.deps import get_ai_provider, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import AI_LIMIT, account_or_ip, limiter
from app.models.user import User
from app.schemas.ai import AIOutputList, AIOutputResponse, AIStatus
from app.services.ai import AIBadOutput, AIProvider, AIRateLimited, AITask, AIUnavailable
from app.services.ai_service import (
    AIService,
    ApplicationNotFound,
    MissingInput,
    ai_status,
)
from app.services.rate_events import DurableLimiter, TooManyAttempts, ai_bucket

router = APIRouter()

_NO_APPLICATION = HTTPException(
    status_code=http_status.HTTP_404_NOT_FOUND, detail="Application not found"
)


@router.get("/status", response_model=AIStatus, summary="Is AI available")
def get_status(
    current_user: User = Depends(get_current_user),
    provider: AIProvider = Depends(get_ai_provider),
) -> AIStatus:
    """Lets the UI explain why AI is unavailable instead of failing on click."""
    enabled, name, detail = ai_status(provider)
    return AIStatus(enabled=enabled, provider=name, detail=detail)


@router.get(
    "/applications/{application_id}",
    response_model=AIOutputList,
    summary="Everything generated for an application",
)
def list_outputs(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(get_ai_provider),
) -> AIOutputList:
    try:
        outputs = AIService(db, provider).list_outputs(current_user.id, application_id)
    except ApplicationNotFound as exc:
        raise _NO_APPLICATION from exc
    return AIOutputList(items=[AIOutputResponse.from_output(o) for o in outputs])


@router.post(
    "/applications/{application_id}/{task}",
    response_model=AIOutputResponse,
    summary="Generate, or return what was generated before",
)
@limiter.limit(AI_LIMIT, key_func=account_or_ip)
def generate(
    request: Request,
    response: Response,
    application_id: uuid.UUID,
    task: AITask,
    force: bool = Query(default=False, description="Regenerate even if cached"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(get_ai_provider),
) -> AIOutputResponse:
    """Cached by default. Generations cost seconds and quota, so repeat views
    reuse the stored answer unless the inputs changed or force is set."""
    # A second, durable cap on top of the in-memory hourly one. The in-memory
    # limit forgets everything when the process restarts, and this host sleeps
    # when idle — so on its own it would hand back a full allowance several
    # times a day on the one endpoint that spends real money.
    limits = DurableLimiter(db)
    bucket = ai_bucket(current_user.id)
    window = timedelta(days=1)
    try:
        limits.check(bucket, limit=settings.AI_DAILY_LIMIT, window=window)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have reached today's limit for AI generations.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    try:
        output = AIService(db, provider).generate(
            current_user.id, application_id, task, force=force
        )
    except ApplicationNotFound as exc:
        raise _NO_APPLICATION from exc
    except MissingInput as exc:
        # The request was fine; the application isn't ready for it yet.
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except AIRateLimited as exc:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except (AIUnavailable, AIBadOutput) as exc:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    # Only a real generation counts. A cached answer never reached the model,
    # so charging it against the allowance would mean simply reopening an
    # application used up the day's budget.
    if not getattr(output, "from_cache", False):
        limits.record(bucket, window=window)

    return AIOutputResponse.from_output(output)
