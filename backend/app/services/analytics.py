"""Turns the aggregate queries into the shape the analytics page renders.

The only real judgement here is when to show a percentage. Everything else is
assembly.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enums import ApplicationStatus
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsSummary,
    FunnelStep,
    SourceStat,
    StageDuration,
    StatusCount,
    Totals,
    VolumePoint,
)

#: Applications needed before any percentage is calculated.
#:
#: Below this, a rate is arithmetic rather than information — one offer out of
#: two applications is a 50% offer rate and means nothing at all. Counts are
#: shown from the very first application; only the percentages wait.
MIN_SAMPLE = 5

#: Sources are judged against a lower bar. Someone with forty applications
#: spread over six job boards would otherwise never see a per-source number,
#: which is the comparison the page exists to make.
MIN_SOURCE_SAMPLE = 3

#: How much history the weekly chart covers.
VOLUME_WEEKS = 12

# Order matters: this is drawn top to bottom as the funnel.
FUNNEL_STEPS: list[tuple[str, str]] = [
    ("applied", "Applied"),
    ("assessment", "Assessment"),
    ("interview", "Interview"),
    ("final", "Final round"),
    ("offer", "Offer"),
    ("accepted", "Accepted"),
]


def _rate(part: int, whole: int, *, floor: int = MIN_SAMPLE) -> float | None:
    """A proportion, or nothing when the denominator is too thin to trust."""
    if whole < floor or whole == 0:
        return None
    return round(part / whole, 4)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.repo = AnalyticsRepository(db)

    def summary(self, user_id: uuid.UUID) -> AnalyticsSummary:
        now = datetime.now(UTC)

        pipeline = self.repo.pipeline(user_id)
        totals = self.repo.totals(user_id)
        response = self.repo.response_time(user_id)

        applied = pipeline.applied
        enough = applied >= MIN_SAMPLE

        reached = {
            "applied": pipeline.applied,
            "assessment": pipeline.assessment,
            "interview": pipeline.interview,
            "final": pipeline.final,
            "offer": pipeline.offer,
            "accepted": pipeline.accepted,
        }

        return AnalyticsSummary(
            generated_at=now,
            min_sample=MIN_SAMPLE,
            has_enough_data=enough,
            totals=Totals(
                applications=totals.applications,
                active=totals.active,
                closed=totals.closed,
                applied=applied,
                interviews_scheduled=totals.interviews_scheduled,
                offers=pipeline.offer,
                response_rate=_rate(pipeline.responded, applied),
                interview_rate=_rate(pipeline.interview, applied),
                offer_rate=_rate(pipeline.offer, applied),
                # Held to the same bar as the rates: a median of two numbers is
                # just the midpoint of two numbers.
                median_days_to_response=(
                    round(response.median_days, 1)
                    if response.median_days is not None and response.samples >= MIN_SAMPLE
                    else None
                ),
                response_samples=response.samples,
            ),
            funnel=[
                FunnelStep(
                    key=key,
                    label=label,
                    count=reached[key],
                    # Measured against applications actually sent, so a pile of
                    # wishlist entries doesn't dilute every stage below it.
                    rate=_rate(reached[key], applied),
                )
                for key, label in FUNNEL_STEPS
            ],
            statuses=[
                StatusCount(status=ApplicationStatus(row.status), count=row.total)
                for row in self.repo.statuses(user_id)
            ],
            stage_durations=[
                StageDuration(
                    status=ApplicationStatus(row.status),
                    average_days=round(row.average_days, 1),
                    median_days=round(row.median_days, 1),
                    moves=row.moves,
                )
                for row in self.repo.stage_durations(user_id)
            ],
            sources=[
                SourceStat(
                    source=row.source,
                    total=row.total,
                    sent=row.sent,
                    interviews=row.interviews,
                    offers=row.offers,
                    interview_rate=_rate(row.interviews, row.sent, floor=MIN_SOURCE_SAMPLE),
                )
                for row in self.repo.sources(user_id)
            ],
            volume=[
                VolumePoint(week_start=row.week_start, created=row.created, moved=row.moved)
                for row in self.repo.volume(user_id, since=now - timedelta(weeks=VOLUME_WEEKS))
            ],
        )
