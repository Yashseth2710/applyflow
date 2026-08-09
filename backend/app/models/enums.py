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


class InterviewRound(str, enum.Enum):
    """Finer grained than ApplicationStatus on purpose.

    An application sits in one stage; a stage can contain several interviews,
    and "which round was that" is a different question from "where is this
    application".
    """

    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    TAKE_HOME = "take_home"
    SYSTEM_DESIGN = "system_design"
    HR = "hr"
    MANAGERIAL = "managerial"
    FINAL = "final"
    OTHER = "other"


class InterviewMode(str, enum.Enum):
    ONSITE = "onsite"
    VIDEO = "video"
    PHONE = "phone"


class InterviewOutcome(str, enum.Enum):
    """PENDING covers both "not happened yet" and "happened, still waiting" —
    the scheduled time tells those apart without a second field."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


#: Outcomes that mean nothing further is expected of this interview.
SETTLED_OUTCOMES: frozenset[InterviewOutcome] = frozenset(
    {
        InterviewOutcome.PASSED,
        InterviewOutcome.FAILED,
        InterviewOutcome.CANCELLED,
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
