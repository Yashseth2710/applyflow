"""Limits that have to survive a restart.

The in-memory limiter in `app/core/rate_limit.py` is the cheap first line: it
stops one address flooding one endpoint without touching the database. It has
two blind spots this covers.

It forgets everything when the process restarts, and on a host that sleeps
after a few idle minutes a restart is routine rather than exceptional — so an
hourly limit held in memory is not really hourly.

And it counts addresses. That is the right unit for a flood and the wrong one
for a guessing attack: ten thousand attempts spread one-per-address across a
botnet never trip an address limit, while the account being guessed at is the
same account every time. Counting the account instead is what actually slows
that down.

Both layers stay. They answer different questions, and the cheap one keeps most
traffic away from the expensive one.
"""

import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.rate_event import RateEvent

#: Nothing here is interesting for longer than this, so the sweep can be brutal.
RETENTION = timedelta(days=1)

#: Fraction of writes that also sweep expired rows across every bucket. Each
#: write already prunes its own bucket, which handles anything being used;
#: this is for the buckets nobody comes back to — a run through ten thousand
#: made-up email addresses leaves ten thousand of them.
SWEEP_CHANCE = 0.02


class TooManyAttempts(Exception):
    """Raised instead of doing the thing. `retry_after` is in seconds."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Too many attempts. Try again in {retry_after} seconds.")
        self.retry_after = retry_after


def login_bucket(email: str) -> str:
    """Keyed on the email, and recorded whether or not that account exists.

    Counting only real accounts would leak the thing login is careful not to
    say: an attacker who sees 429 for one address and 401 for another has just
    learned which one is registered, which undoes the deliberate choice to give
    the same answer for "no such user" and "wrong password".
    """
    return f"login:{email.strip().lower()}"


def ai_bucket(user_id: uuid.UUID) -> str:
    return f"ai:{user_id}"


def upload_bucket(user_id: uuid.UUID) -> str:
    return f"upload:{user_id}"


def register_bucket(address: str) -> str:
    """Keyed on the address, because there is no account yet to key on.

    Durable rather than in-memory for the one reason that matters here: an
    account created during a burst does not disappear when the process
    restarts, so neither should the record of having created it. An in-memory
    count hands back a full allowance every time the host wakes up, which on a
    tier that sleeps when idle is several times a day.
    """
    return f"register:{address}"


class DurableLimiter:
    def __init__(self, db: Session) -> None:
        self.db = db

    def check(self, bucket: str, *, limit: int, window: timedelta) -> None:
        """Raise if the bucket is already full, without recording anything.

        Separate from `record` so an attempt can be refused before the work is
        done — there is no point verifying a password, or calling a paid model,
        for a request that is going to be rejected either way.
        """
        since = datetime.now(UTC) - window
        used = self._count(bucket, since)
        if used < limit:
            return

        oldest = self.db.execute(
            select(func.min(RateEvent.created_at)).where(
                RateEvent.bucket == bucket, RateEvent.created_at >= since
            )
        ).scalar_one_or_none()

        # The window is a sliding one, so the wait is until the oldest attempt
        # still being counted drops out of it, not a flat cooldown.
        wait = window - (datetime.now(UTC) - oldest) if oldest else window
        raise TooManyAttempts(max(1, int(wait.total_seconds())))

    def record(self, bucket: str, *, window: timedelta) -> None:
        """Count one attempt, and tidy up behind it."""
        self.db.add(RateEvent(bucket=bucket))
        self._prune(bucket, window)
        self.db.commit()

    def clear(self, bucket: str) -> None:
        """Forget a bucket. Called when a login succeeds: the attempts were a
        person misremembering their own password, not an attack, and holding
        them against the next honest attempt would be its own kind of failure."""
        self.db.execute(delete(RateEvent).where(RateEvent.bucket == bucket))
        self.db.commit()

    def _count(self, bucket: str, since: datetime) -> int:
        return (
            self.db.execute(
                select(func.count())
                .select_from(RateEvent)
                .where(RateEvent.bucket == bucket, RateEvent.created_at >= since)
            ).scalar_one()
            or 0
        )

    def _prune(self, bucket: str, window: timedelta) -> None:
        self.db.execute(
            delete(RateEvent).where(
                RateEvent.bucket == bucket,
                RateEvent.created_at < datetime.now(UTC) - window,
            )
        )
        if random.random() < SWEEP_CHANCE:
            self.db.execute(
                delete(RateEvent).where(RateEvent.created_at < datetime.now(UTC) - RETENTION)
            )
