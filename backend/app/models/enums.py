"""Shared enums.

These become native Postgres enum types, so adding a value needs a migration.
Worth it — the database rejects invalid states instead of trusting the app.
"""

import enum


class CareerLevel(str, enum.Enum):
    """`str` mixin so Pydantic serialises the value, not `CareerLevel.STUDENT`."""

    STUDENT = "student"
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class ApplicationStatus(str, enum.Enum):
    """Not a state machine — real job searches skip stages, go backwards and
    revive dead applications. Any transition is allowed; history records it."""

    WISHLIST = "wishlist"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL_INTERVIEW = "technical_interview"
    HR_INTERVIEW = "hr_interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    ACCEPTED = "accepted"
    # Terminal outcomes.
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ON_HOLD = "on_hold"


#: No longer being actively pursued. The board collapses these into "Closed".
CLOSED_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.ON_HOLD,
    }
)

#: Statuses that mean an interview happened. Used by analytics to
#: compute application -> interview conversion.
INTERVIEW_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.TECHNICAL_INTERVIEW,
        ApplicationStatus.HR_INTERVIEW,
        ApplicationStatus.FINAL_INTERVIEW,
    }
)


class ExtractionStatus(str, enum.Enum):
    """Outcome of pulling text out of an uploaded file.

    EMPTY is separate from FAILED on purpose: a scanned resume parses fine and
    yields nothing, and telling someone their file is unreadable is more useful
    than showing a blank page.
    """

    PENDING = "pending"
    OK = "ok"
    EMPTY = "empty"
    FAILED = "failed"


class WorkMode(str, enum.Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
