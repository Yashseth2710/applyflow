"""Analytics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary, summary="Job search statistics")
def summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsSummary:
    """Everything the analytics page shows, in one request.

    One endpoint rather than several: the page draws all of it at once, and
    six round trips to a database that sleeps when idle would mean six cold
    starts instead of one.
    """
    return AnalyticsService(db).summary(current_user.id)
