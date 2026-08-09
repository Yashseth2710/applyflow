"""Enums shared across models.

These become native PostgreSQL enum types via Alembic. Adding a value later
requires a migration (ALTER TYPE ... ADD VALUE), which is a deliberate
trade-off: the database rejects invalid states rather than trusting the app.
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
    """Where an application currently sits.

    Deliberately NOT a state machine: real job searches skip stages, go
    backwards, and revive dead applications. Any transition is allowed; the
    history table records what actually happened.
    """

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


#: Statuses an application has left, i.e. no longer being actively pursued.
#: The board groups these into a collapsed "Closed" section rather than giving
#: each its own column. See docs/roadmap.md.
CLOSED_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.ON_HOLD,
    }
)

#: Statuses that mean an interview happened. Used by the analytics milestone to
#: compute application -> interview conversion.
INTERVIEW_STATUSES: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.TECHNICAL_INTERVIEW,
        ApplicationStatus.HR_INTERVIEW,
        ApplicationStatus.FINAL_INTERVIEW,
    }
)


class WorkMode(str, enum.Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
