"""Health check — probes the database for real."""

import logging
import time

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import DatabaseHealth, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service and database health",
)
def health_check(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    """Runs a real `SELECT 1` rather than reporting a hardcoded value.

    Returns 503 when the database is unreachable so uptime monitors and
    container orchestrators see the failure.
    """
    started = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        db_health = DatabaseHealth(connected=True, latency_ms=latency_ms)
        overall = "ok"
    except SQLAlchemyError as exc:
        # Log the detail, return something generic — connection strings and
        # host names must not leak to unauthenticated callers.
        logger.exception("Health check database probe failed")
        db_health = DatabaseHealth(connected=False, error="database unreachable")
        overall = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        _ = exc

    return HealthResponse(
        status=overall,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_health,
    )
