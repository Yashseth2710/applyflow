"""Read-only aggregates for the analytics page.

Written as SQL rather than through the ORM. These are window functions,
percentiles and filtered counts over the whole table — the kind of thing the
query builder can express but nobody can read afterwards — and every one of
them is a single round trip that returns a handful of numbers. Same rule as
everywhere else applies: user_id is a bound parameter on every query.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Row, text
from sqlalchemy.orm import Session

# How far an application got, as a number, so "reached at least the interview
# stage" becomes a comparison instead of a list of statuses.
#
# Terminal statuses (rejected, withdrawn, on_hold) score zero: they say how a
# journey ended, not how far it travelled. The stage reached before them is
# still in the history, and that is what counts.
_RANK_CASE = """
    CASE r.status
        WHEN 'applied' THEN 1
        WHEN 'assessment' THEN 2
        WHEN 'phone_screen' THEN 3
        WHEN 'technical_interview' THEN 3
        WHEN 'hr_interview' THEN 3
        WHEN 'final_interview' THEN 4
        WHEN 'offer' THEN 5
        WHEN 'accepted' THEN 6
        ELSE 0
    END
"""

# Every status an application has ever held, collapsed to the furthest one.
#
# The union with the applications table is belt and braces: history is written
# on create and on every change, so it should already contain the current
# status. Should is doing a lot of work in a table that feeds someone's
# offer rate, and a union is cheaper than being wrong.
_APP_RANK = f"""
    WITH reached AS (
        SELECT application_id, to_status AS status
        FROM application_status_history
        WHERE user_id = :user_id
        UNION
        SELECT id, status
        FROM applications
        WHERE user_id = :user_id
    ),
    app_rank AS (
        SELECT r.application_id,
               max({_RANK_CASE}) AS rank,
               bool_or(r.status = 'rejected') AS rejected
        FROM reached r
        GROUP BY r.application_id
    )
"""


class AnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _one(self, sql: str, **params: Any) -> Row:
        return self.db.execute(text(sql), params).one()

    def _all(self, sql: str, **params: Any) -> list[Row]:
        return list(self.db.execute(text(sql), params).all())

    def pipeline(self, user_id: uuid.UUID) -> Row:
        """One row of cumulative counts: how many applications reached each rung.

        Cumulative on purpose. A funnel where a later stage outnumbers an
        earlier one looks broken, and it would happen constantly — people log
        the interview they got without ever having ticked "assessment".
        """
        return self._one(
            f"""
            {_APP_RANK}
            SELECT count(*) FILTER (WHERE rank >= 1)               AS applied,
                   count(*) FILTER (WHERE rank >= 2)               AS assessment,
                   count(*) FILTER (WHERE rank >= 3)               AS interview,
                   count(*) FILTER (WHERE rank >= 4)               AS final,
                   count(*) FILTER (WHERE rank >= 5)               AS offer,
                   count(*) FILTER (WHERE rank >= 6)               AS accepted,
                   -- A rejection is a reply. Counting only the applications
                   -- that advanced would call a "no" the same as silence.
                   count(*) FILTER (WHERE rank >= 2 OR rejected)   AS responded
            FROM app_rank
            """,
            user_id=user_id,
        )

    def totals(self, user_id: uuid.UUID) -> Row:
        return self._one(
            """
            SELECT
                (SELECT count(*) FROM applications WHERE user_id = :user_id)
                    AS applications,
                (SELECT count(*) FROM applications
                  WHERE user_id = :user_id
                    AND status NOT IN ('rejected', 'withdrawn', 'on_hold'))
                    AS active,
                (SELECT count(*) FROM applications
                  WHERE user_id = :user_id
                    AND status IN ('rejected', 'withdrawn', 'on_hold'))
                    AS closed,
                (SELECT count(*) FROM interviews WHERE user_id = :user_id)
                    AS interviews_scheduled
            """,
            user_id=user_id,
        )

    def statuses(self, user_id: uuid.UUID) -> list[Row]:
        return self._all(
            """
            -- Aliased "total" rather than "count": a Row is a tuple, and
            -- row.count would quietly hand back tuple.count instead of the
            -- number.
            SELECT status, count(*) AS total
            FROM applications
            WHERE user_id = :user_id
            GROUP BY status
            """,
            user_id=user_id,
        )

    def stage_durations(self, user_id: uuid.UUID) -> list[Row]:
        """Average and median days spent in each stage before moving on.

        `lead` pairs each history entry with the next one for the same
        application; the gap between them is how long it sat in `to_status`.
        The most recent entry has no next one, so a stage an application is
        still in contributes nothing — which is the point, since it hasn't
        finished yet.
        """
        return self._all(
            """
            SELECT status,
                   avg(days)::float8                                        AS average_days,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY days)::float8 AS median_days,
                   count(*)                                                 AS moves
            FROM (
                SELECT h.to_status AS status,
                       EXTRACT(EPOCH FROM (
                           lead(h.changed_at) OVER (
                               PARTITION BY h.application_id ORDER BY h.changed_at
                           ) - h.changed_at
                       )) / 86400 AS days
                FROM application_status_history h
                WHERE h.user_id = :user_id
            ) stays
            WHERE days IS NOT NULL
            GROUP BY status
            """,
            user_id=user_id,
        )

    def response_time(self, user_id: uuid.UUID) -> Row:
        """How long the first reply takes, measured from the day of applying.

        Median rather than average: one application answered eight months later
        would move an average enough to make it useless.
        """
        return self._one(
            """
            WITH applied_at AS (
                SELECT application_id, min(changed_at) AS at
                FROM application_status_history
                WHERE user_id = :user_id AND to_status = 'applied'
                GROUP BY application_id
            ),
            first_reply AS (
                SELECT h.application_id, min(h.changed_at) AS at
                FROM application_status_history h
                JOIN applied_at a ON a.application_id = h.application_id
                WHERE h.user_id = :user_id
                  AND h.changed_at > a.at
                  -- Moving back to wishlist, or re-marking applied, is the
                  -- user tidying up rather than the company replying.
                  AND h.to_status NOT IN ('applied', 'wishlist')
                GROUP BY h.application_id
            )
            SELECT percentile_cont(0.5) WITHIN GROUP (
                       ORDER BY EXTRACT(EPOCH FROM (f.at - a.at)) / 86400
                   )::float8 AS median_days,
                   count(*)  AS samples
            FROM first_reply f
            JOIN applied_at a ON a.application_id = f.application_id
            """,
            user_id=user_id,
        )

    def sources(self, user_id: uuid.UUID) -> list[Row]:
        """Which channels actually lead somewhere."""
        return self._all(
            f"""
            {_APP_RANK}
            SELECT a.source,
                   count(*)                                 AS total,
                   -- Rates are measured against what was actually sent. A
                   -- source with three wishlist entries and no applications
                   -- has not converted 0% of anything.
                   count(*) FILTER (WHERE ar.rank >= 1)     AS sent,
                   count(*) FILTER (WHERE ar.rank >= 3)     AS interviews,
                   count(*) FILTER (WHERE ar.rank >= 5)     AS offers
            FROM applications a
            JOIN app_rank ar ON ar.application_id = a.id
            WHERE a.user_id = :user_id
            GROUP BY a.source
            ORDER BY count(*) DESC, a.source NULLS LAST
            """,
            user_id=user_id,
        )

    def volume(self, user_id: uuid.UUID, *, since: datetime) -> list[Row]:
        """Week by week: applications added, and stages moved.

        Weeks come from `generate_series` rather than from the data, so quiet
        weeks appear as zero instead of vanishing and making a gap look like
        steady activity. Buckets follow the database's timezone, which is UTC —
        near enough for a weekly chart.
        """
        return self._all(
            """
            SELECT w.week_start::date AS week_start,
                   (SELECT count(*) FROM applications a
                     WHERE a.user_id = :user_id
                       AND a.created_at >= w.week_start
                       AND a.created_at < w.week_start + interval '1 week') AS created,
                   (SELECT count(*) FROM application_status_history h
                     WHERE h.user_id = :user_id
                       AND h.from_status IS NOT NULL
                       AND h.changed_at >= w.week_start
                       AND h.changed_at < w.week_start + interval '1 week') AS moved
            FROM (
                SELECT generate_series(
                    -- CAST(...), not `:since::timestamptz`: the two colons run
                    -- together and the parameter never gets bound.
                    date_trunc('week', CAST(:since AS timestamptz)),
                    date_trunc('week', now()),
                    interval '1 week'
                ) AS week_start
            ) w
            ORDER BY w.week_start
            """,
            user_id=user_id,
            since=since,
        )
