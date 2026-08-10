"""Limits that outlive the process.

The in-memory limiter is switched off for the whole suite (see conftest), so
everything failing here is failing on the durable layer alone — which is the
point: it has to work when the other one has forgotten everything.
"""

import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.rate_event import RateEvent
from app.services.rate_events import (
    DurableLimiter,
    TooManyAttempts,
    login_bucket,
)

PASSWORD = "correct-horse-battery"


def _pdf(size: int = 400) -> bytes:
    body = b"%PDF-1.4\n" + b"x" * size
    return body + b"\n%%EOF\n"


# ---- login ----


def test_guessing_one_account_runs_out(client: TestClient, registered_user: dict) -> None:
    email = registered_user["email"]

    codes = [
        client.post(
            "/api/v1/auth/login", json={"email": email, "password": f"wrong-{i}"}
        ).status_code
        for i in range(settings.LOGIN_ATTEMPT_LIMIT + 1)
    ]

    assert codes[: settings.LOGIN_ATTEMPT_LIMIT] == [401] * settings.LOGIN_ATTEMPT_LIMIT
    assert codes[-1] == 429


def test_the_lockout_survives_a_restart(
    client: TestClient, registered_user: dict, db_session: Session
) -> None:
    """The whole reason this is in the database rather than in memory.

    The host sleeps when idle, so a restart is a routine event. Simulated here
    by clearing the in-memory limiter, which is what a restart does to it.
    """
    from app.core.rate_limit import limiter

    email = registered_user["email"]
    for i in range(settings.LOGIN_ATTEMPT_LIMIT):
        client.post("/api/v1/auth/login", json={"email": email, "password": f"no-{i}"})

    limiter.reset()

    r = client.post("/api/v1/auth/login", json={"email": email, "password": "no-again"})
    assert r.status_code == 429


def test_an_unknown_email_locks_exactly_like_a_real_one(client: TestClient) -> None:
    """Otherwise 429-versus-401 answers the question login refuses to: whether
    this address has an account."""
    unknown = f"nobody-{uuid.uuid4().hex[:8]}@example.com"

    codes = [
        client.post("/api/v1/auth/login", json={"email": unknown, "password": "guess"}).status_code
        for _ in range(settings.LOGIN_ATTEMPT_LIMIT + 1)
    ]

    assert codes[: settings.LOGIN_ATTEMPT_LIMIT] == [401] * settings.LOGIN_ATTEMPT_LIMIT
    assert codes[-1] == 429


def test_the_two_lockouts_say_the_same_thing(client: TestClient, registered_user: dict) -> None:
    unknown = f"nobody-{uuid.uuid4().hex[:8]}@example.com"

    def exhaust(email: str) -> dict:
        last = None
        for _ in range(settings.LOGIN_ATTEMPT_LIMIT + 1):
            last = client.post("/api/v1/auth/login", json={"email": email, "password": "guess"})
        assert last is not None
        return last.json()

    assert exhaust(registered_user["email"]) == exhaust(unknown)


def test_the_right_password_clears_the_count(client: TestClient, registered_user: dict) -> None:
    """Someone misremembering their own password must not be left one attempt
    from being locked out for the rest of the window."""
    for i in range(settings.LOGIN_ATTEMPT_LIMIT - 1):
        client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": f"no-{i}"},
        )

    ok = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": PASSWORD},
    )
    assert ok.status_code == 200

    # A fresh run of wrong answers, right up to the limit, still gets through.
    codes = [
        client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": f"again-{i}"},
        ).status_code
        for i in range(settings.LOGIN_ATTEMPT_LIMIT)
    ]
    assert codes == [401] * settings.LOGIN_ATTEMPT_LIMIT


def test_locking_one_account_leaves_others_alone(
    client: TestClient, registered_user: dict, other_user: dict
) -> None:
    """An address limit would have caught the second account in the blast."""
    for i in range(settings.LOGIN_ATTEMPT_LIMIT + 1):
        client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": f"no-{i}"},
        )

    r = client.post(
        "/api/v1/auth/login",
        json={"email": other_user["email"], "password": PASSWORD},
    )
    assert r.status_code == 200


def test_the_wait_shrinks_as_attempts_age_out(db_session: Session) -> None:
    """A sliding window, not a flat cooldown: the wait is until the oldest
    attempt still counted drops out."""
    limits = DurableLimiter(db_session)
    bucket = login_bucket(f"slide-{uuid.uuid4().hex[:8]}@example.com")
    window = timedelta(minutes=15)

    for _ in range(3):
        limits.record(bucket, window=window)

    # Age two of them almost out of the window.
    db_session.execute(
        text(
            "UPDATE rate_events SET created_at = :t WHERE bucket = :b "
            "AND id IN (SELECT id FROM rate_events WHERE bucket = :b LIMIT 2)"
        ),
        {"t": datetime.now(UTC) - timedelta(minutes=14), "b": bucket},
    )

    with pytest.raises(TooManyAttempts) as caught:
        limits.check(bucket, limit=3, window=window)

    assert 0 < caught.value.retry_after <= 61


def test_attempts_older_than_the_window_stop_counting(db_session: Session) -> None:
    limits = DurableLimiter(db_session)
    bucket = login_bucket(f"old-{uuid.uuid4().hex[:8]}@example.com")
    window = timedelta(minutes=15)

    for _ in range(5):
        limits.record(bucket, window=window)
    db_session.execute(
        text("UPDATE rate_events SET created_at = :t WHERE bucket = :b"),
        {"t": datetime.now(UTC) - timedelta(minutes=20), "b": bucket},
    )

    # No exception: everything recorded has aged out.
    limits.check(bucket, limit=5, window=window)


def test_recording_clears_out_expired_rows(db_session: Session) -> None:
    """Rows are worthless past their window, and this table sees a row per
    guess — a run through ten thousand addresses should not be left behind."""
    limits = DurableLimiter(db_session)
    bucket = login_bucket(f"prune-{uuid.uuid4().hex[:8]}@example.com")
    window = timedelta(minutes=15)

    limits.record(bucket, window=window)
    db_session.execute(
        text("UPDATE rate_events SET created_at = :t WHERE bucket = :b"),
        {"t": datetime.now(UTC) - timedelta(hours=2), "b": bucket},
    )
    limits.record(bucket, window=window)

    remaining = (
        db_session.query(RateEvent).filter(RateEvent.bucket == bucket).count()  # type: ignore[attr-defined]
    )
    assert remaining == 1


# ---- storage quota ----


def test_uploads_stop_at_the_storage_quota(
    client: TestClient, registered_user: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A per-file cap bounds nothing: the same file, sent again and again, is
    inside every per-file rule and still fills the database."""
    # One kilobyte of headroom, so two small files is one too many.
    monkeypatch.setattr(settings, "MAX_STORAGE_PER_USER_MB", 0)
    monkeypatch.setattr(type(settings), "max_storage_per_user_bytes", property(lambda _: 1000))

    first = client.post(
        "/api/v1/resumes",
        headers=registered_user["headers"],
        files={"file": ("a.pdf", io.BytesIO(_pdf(400)), "application/pdf")},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/resumes",
        headers=registered_user["headers"],
        files={"file": ("b.pdf", io.BytesIO(_pdf(900)), "application/pdf")},
    )

    assert second.status_code == 413
    # The file is fine; it is the total that is not. The message has to say so,
    # or it reads as "your PDF is broken".
    assert "storage limit" in second.json()["detail"]


def test_the_limits_stay_readable_without_signing_in(client: TestClient) -> None:
    """Adding the per-account figures must not turn a public endpoint private.

    The file rules are the same for everyone; only the usage numbers need to
    know who is asking.
    """
    r = client.get("/api/v1/resumes/limits")

    assert r.status_code == 200
    body = r.json()
    assert body["max_size_bytes"] == settings.max_upload_bytes
    assert "storage_used_bytes" not in body


def test_the_quota_is_reported_before_uploading(client: TestClient, registered_user: dict) -> None:
    """So the client can refuse a file it knows will not fit, rather than
    spending a minute sending it first."""
    r = client.get("/api/v1/resumes/limits", headers=registered_user["headers"])

    body = r.json()
    assert body["storage_used_bytes"] == 0
    assert body["storage_limit_bytes"] == settings.max_storage_per_user_bytes
    assert body["storage_remaining_bytes"] == settings.max_storage_per_user_bytes


def test_deleting_a_resume_gives_the_room_back(client: TestClient, registered_user: dict) -> None:
    upload = client.post(
        "/api/v1/resumes",
        headers=registered_user["headers"],
        files={"file": ("a.pdf", io.BytesIO(_pdf(400)), "application/pdf")},
    )
    assert upload.status_code == 201
    used = client.get("/api/v1/resumes/limits", headers=registered_user["headers"]).json()
    assert used["storage_used_bytes"] > 0

    client.delete(f"/api/v1/resumes/{upload.json()['id']}", headers=registered_user["headers"])

    after = client.get("/api/v1/resumes/limits", headers=registered_user["headers"]).json()
    assert after["storage_used_bytes"] == 0


def test_registrations_from_one_address_are_counted_in_the_database(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The in-memory limit forgets everything on restart, and this host sleeps
    when idle — but the accounts it let through are still there."""
    monkeypatch.setattr(settings, "REGISTER_DAILY_LIMIT", 3)

    def register() -> int:
        return client.post(
            "/api/v1/auth/register",
            json={
                "email": f"reg-{uuid.uuid4().hex[:10]}@example.com",
                "password": PASSWORD,
                "first_name": "Test",
                "last_name": "User",
            },
        ).status_code

    codes = [register() for _ in range(4)]

    assert codes[:3] == [201] * 3
    assert codes[3] == 429


def test_a_duplicate_email_does_not_cost_a_registration(
    client: TestClient, registered_user: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No account was created, so nothing was spent. Otherwise retyping an
    address you already used burns a household's daily allowance."""
    monkeypatch.setattr(settings, "REGISTER_DAILY_LIMIT", 2)

    for _ in range(3):
        r = client.post(
            "/api/v1/auth/register",
            json={
                "email": registered_user["email"],
                "password": PASSWORD,
                "first_name": "Test",
                "last_name": "User",
            },
        )
        assert r.status_code == 409

    fresh = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"reg-{uuid.uuid4().hex[:10]}@example.com",
            "password": PASSWORD,
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert fresh.status_code == 201


# ---- rows ----


def test_applications_stop_at_the_per_account_cap(
    client: TestClient, registered_user: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Capping the length of one job description bounds a request, not an
    account. Rows are the other way into a database with a size ceiling."""
    monkeypatch.setattr(settings, "MAX_APPLICATIONS_PER_USER", 2)

    codes = [
        client.post(
            "/api/v1/applications",
            headers=registered_user["headers"],
            json={"company_name": f"Co {i}", "job_title": "Engineer"},
        ).status_code
        for i in range(3)
    ]

    assert codes[:2] == [201, 201]
    # 409, not 429: waiting changes nothing, deleting something does.
    assert codes[2] == 409


def test_a_job_description_cannot_be_unbounded(client: TestClient, registered_user: dict) -> None:
    r = client.post(
        "/api/v1/applications",
        headers=registered_user["headers"],
        json={
            "company_name": "Acme",
            "job_title": "Engineer",
            "job_description": "x" * 50_001,
        },
    )

    assert r.status_code == 422


def test_interview_notes_cannot_be_unbounded(client: TestClient, registered_user: dict) -> None:
    created = client.post(
        "/api/v1/applications",
        headers=registered_user["headers"],
        json={"company_name": "Acme", "job_title": "Engineer"},
    )
    r = client.post(
        "/api/v1/interviews",
        headers=registered_user["headers"],
        json={
            "application_id": created.json()["id"],
            "round": "technical",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "notes": "x" * 10_001,
        },
    )

    assert r.status_code == 422


def test_interviews_stop_at_the_per_application_cap(
    client: TestClient, registered_user: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "MAX_INTERVIEWS_PER_APPLICATION", 2)
    created = client.post(
        "/api/v1/applications",
        headers=registered_user["headers"],
        json={"company_name": "Acme", "job_title": "Engineer"},
    )
    application_id = created.json()["id"]

    codes = [
        client.post(
            "/api/v1/interviews",
            headers=registered_user["headers"],
            json={
                "application_id": application_id,
                "round": "technical",
                "scheduled_at": (datetime.now(UTC) + timedelta(days=i + 1)).isoformat(),
            },
        ).status_code
        for i in range(3)
    ]

    assert codes[:2] == [201, 201]
    assert codes[2] == 409


def test_a_rejected_upload_does_not_cost_an_attempt(
    client: TestClient, registered_user: dict, db_session: Session
) -> None:
    """Otherwise a loop of invalid files exhausts the caller's own allowance,
    which is a way to lock someone out of their own account."""
    for _ in range(3):
        r = client.post(
            "/api/v1/resumes",
            headers=registered_user["headers"],
            files={"file": ("a.txt", io.BytesIO(b"not a pdf"), "text/plain")},
        )
        assert r.status_code == 422

    recorded = (
        db_session.query(RateEvent)  # type: ignore[attr-defined]
        .filter(RateEvent.bucket == f"upload:{registered_user['id']}")
        .count()
    )
    assert recorded == 0
