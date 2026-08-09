"""Analytics schemas.

Counts are always reported. Percentages are not: a single offer out of three
applications is a 33% offer rate, which reads like a finding and is really just
noise. Rate fields are therefore optional, and the service leaves them null
until there is enough behind them to mean something.
"""

from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import ApplicationStatus


class Totals(BaseModel):
    """The headline numbers, and the rates that only appear once earned."""

    applications: int
    active: int
    closed: int
    #: Applications that were actually sent, i.e. that reached "applied" or
    #: past it. The denominator for every rate below.
    applied: int
    interviews_scheduled: int
    offers: int

    response_rate: float | None
    interview_rate: float | None
    offer_rate: float | None

    #: Typical wait between applying and the first sign of life.
    median_days_to_response: float | None
    #: How many applications that median is drawn from, so the UI can say.
    response_samples: int


class FunnelStep(BaseModel):
    """One rung of the pipeline, counted as "ever reached, not still here".

    An application that was rejected after a final round still counts towards
    every earlier step — otherwise the funnel would only describe applications
    that are currently in flight, which is the least interesting group.
    """

    key: str
    label: str
    count: int
    #: Share of applied applications that got at least this far.
    rate: float | None


class StatusCount(BaseModel):
    """Where things stand right now. No label — the client already owns the
    wording and the colour for each status."""

    status: ApplicationStatus
    count: int


class StageDuration(BaseModel):
    """How long applications sit in a stage before moving on.

    Only completed stays count. An application still sitting in a stage has no
    end date, and treating "so far" as "took" would drag every average down.
    """

    status: ApplicationStatus
    average_days: float
    median_days: float
    #: Completed stays behind the numbers.
    moves: int


class SourceStat(BaseModel):
    """Per job board / referral / careers page.

    Sources are grouped exactly as typed. Folding "LinkedIn" into "linkedin"
    means guessing, and a wrong guess quietly merges two real answers.
    """

    source: str | None
    total: int
    #: Of those, the ones that were actually applied to. The denominator for
    #: the rate, since a wishlist entry has not converted at anything.
    sent: int
    interviews: int
    offers: int
    interview_rate: float | None


class VolumePoint(BaseModel):
    """One week of activity."""

    week_start: date
    #: Applications added.
    created: int
    #: Status changes recorded, excluding the entry written at creation.
    moved: int


class AnalyticsSummary(BaseModel):
    generated_at: datetime
    #: Applications needed before rates are calculated at all.
    min_sample: int
    #: False while the numbers above are still too thin for percentages.
    has_enough_data: bool

    totals: Totals
    funnel: list[FunnelStep]
    statuses: list[StatusCount]
    stage_durations: list[StageDuration]
    sources: list[SourceStat]
    volume: list[VolumePoint]
