"""Interview scheduling, outcomes, access control, and derived reminders."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient


def iso(offset: timedelta) -> str:
    """A timezone-aware timestamp relative to now."""
    return (datetime.now(UTC) + offset).isoformat()


def create_application(client: TestClient, user: dict, **extra: object) -> dict:
    r = client.post(
        "/api/v1/applications",
        headers=user["headers"],
        json={
            "company_name": "Acme",
            "job_title": "Backend Engineer",
            "status": "applied",
            **extra,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def schedule(client: TestClient, user: dict, application_id: str, **extra: object):
    payload = {
        "application_id": application_id,
        "round": "technical",
        "scheduled_at": iso(timedelta(days=2)),
        **extra,
    }
    return client.post("/api/v1/interviews", headers=user["headers"], json=payload)


# ---- creating ----


def test_schedule_an_interview(client, registered_user):
    application = create_application(client, registered_user)

    r = schedule(
        client,
        registered_user,
        application["id"],
        mode="video",
        duration_minutes=60,
        location="https://meet.example.com/abc",
        interviewer="Priya",
        notes="Revise system design",
    )
    assert r.status_code == 201, r.text

    body = r.json()
    assert body["round"] == "technical"
    assert body["mode"] == "video"
    assert body["duration_minutes"] == 60
    assert body["interviewer"] == "Priya"
    assert body["outcome"] == "pending"


def test_interview_needs_a_timezone(client, registered_user):
    """A naive time would be read as UTC and quietly move every IST interview."""
    application = create_application(client, registered_user)

    r = schedule(client, registered_user, application["id"], scheduled_at="2026-09-01T10:00:00")
    assert r.status_code == 422
    assert "timezone" in r.text.lower()


def test_cannot_attach_an_interview_to_someone_elses_application(
    client, registered_user, other_user
):
    application = create_application(client, registered_user)

    r = schedule(client, other_user, application["id"])
    assert r.status_code == 404


def test_unknown_application_is_rejected(client, registered_user):
    r = schedule(client, registered_user, "00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_duration_is_bounded(client, registered_user):
    application = create_application(client, registered_user)
    assert (
        schedule(client, registered_user, application["id"], duration_minutes=0).status_code == 422
    )
    assert (
        schedule(client, registered_user, application["id"], duration_minutes=2000).status_code
        == 422
    )


# ---- listing ----


def test_interviews_list_in_time_order(client, registered_user):
    application = create_application(client, registered_user)
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=9)))
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=3)))
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=6)))

    r = client.get(
        f"/api/v1/interviews?application_id={application['id']}",
        headers=registered_user["headers"],
    )
    assert r.status_code == 200
    times = [i["scheduled_at"] for i in r.json()]
    assert times == sorted(times)


def test_upcoming_carries_the_company_and_role(client, registered_user):
    """A bare interview row means nothing outside its application."""
    application = create_application(client, registered_user, company_name="Globex")
    schedule(client, registered_user, application["id"])

    r = client.get("/api/v1/interviews/upcoming", headers=registered_user["headers"])
    assert r.status_code == 200

    row = r.json()[0]
    assert row["company_name"] == "Globex"
    assert row["job_title"] == "Backend Engineer"
    assert row["application_status"] == "applied"


def test_upcoming_excludes_the_past_and_the_settled(client, registered_user):
    application = create_application(client, registered_user)

    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=-1)))
    cancelled = schedule(
        client, registered_user, application["id"], scheduled_at=iso(timedelta(days=1))
    ).json()
    client.patch(
        f"/api/v1/interviews/{cancelled['id']}",
        headers=registered_user["headers"],
        json={"outcome": "cancelled"},
    )
    future = schedule(
        client, registered_user, application["id"], scheduled_at=iso(timedelta(days=4))
    ).json()

    r = client.get("/api/v1/interviews/upcoming", headers=registered_user["headers"])
    assert [i["id"] for i in r.json()] == [future["id"]]


# ---- updating ----


def test_recording_an_outcome(client, registered_user):
    application = create_application(client, registered_user)
    interview = schedule(client, registered_user, application["id"]).json()

    r = client.patch(
        f"/api/v1/interviews/{interview['id']}",
        headers=registered_user["headers"],
        json={"outcome": "passed", "feedback": "  Went well, next round booked  "},
    )
    assert r.status_code == 200
    assert r.json()["outcome"] == "passed"
    assert r.json()["feedback"] == "Went well, next round booked"


def test_an_interview_cannot_be_moved_between_applications(client, registered_user):
    """Rewriting which job an interview belonged to would corrupt the history."""
    application = create_application(client, registered_user)
    other = create_application(client, registered_user, company_name="Initech")
    interview = schedule(client, registered_user, application["id"]).json()

    r = client.patch(
        f"/api/v1/interviews/{interview['id']}",
        headers=registered_user["headers"],
        json={"application_id": other["id"]},
    )
    assert r.status_code == 422


def test_deleting_an_interview(client, registered_user):
    application = create_application(client, registered_user)
    interview = schedule(client, registered_user, application["id"]).json()

    assert (
        client.delete(
            f"/api/v1/interviews/{interview['id']}", headers=registered_user["headers"]
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"/api/v1/interviews/{interview['id']}", headers=registered_user["headers"]
        ).status_code
        == 404
    )


def test_deleting_an_application_takes_its_interviews(client, registered_user):
    application = create_application(client, registered_user)
    interview = schedule(client, registered_user, application["id"]).json()

    client.delete(f"/api/v1/applications/{application['id']}", headers=registered_user["headers"])

    r = client.get(f"/api/v1/interviews/{interview['id']}", headers=registered_user["headers"])
    assert r.status_code == 404


# ---- access control ----


def test_interviews_require_authentication(client):
    assert client.get("/api/v1/interviews/upcoming").status_code == 401
    assert client.get("/api/v1/interviews/reminders").status_code == 401


@pytest.mark.parametrize("method", ["get", "delete"])
def test_another_users_interview_is_not_reachable(client, registered_user, other_user, method):
    application = create_application(client, registered_user)
    interview = schedule(client, registered_user, application["id"]).json()

    r = getattr(client, method)(
        f"/api/v1/interviews/{interview['id']}", headers=other_user["headers"]
    )
    assert r.status_code == 404


def test_another_users_interviews_stay_out_of_upcoming(client, registered_user, other_user):
    application = create_application(client, registered_user)
    schedule(client, registered_user, application["id"])

    r = client.get("/api/v1/interviews/upcoming", headers=other_user["headers"])
    assert r.json() == []


# ---- reminders ----


def reminders(client: TestClient, user: dict) -> list[dict]:
    r = client.get("/api/v1/interviews/reminders", headers=user["headers"])
    assert r.status_code == 200
    return r.json()["items"]


def test_an_interview_this_week_is_a_reminder(client, registered_user):
    application = create_application(client, registered_user, company_name="Globex")
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=2)))

    items = reminders(client, registered_user)
    upcoming = [i for i in items if i["kind"] == "interview_upcoming"]
    assert len(upcoming) == 1
    assert "Globex" in upcoming[0]["title"]
    assert "in 2 days" in upcoming[0]["detail"]


def test_an_interview_further_out_is_not_yet_a_reminder(client, registered_user):
    application = create_application(client, registered_user)
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=20)))

    assert [
        i for i in reminders(client, registered_user) if i["kind"] == "interview_upcoming"
    ] == []


def test_a_past_interview_without_an_outcome_is_chased(client, registered_user):
    application = create_application(client, registered_user, company_name="Initech")
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=-3)))

    items = [
        i for i in reminders(client, registered_user) if i["kind"] == "interview_needs_outcome"
    ]
    assert len(items) == 1
    assert items[0]["severity"] == "warning"
    assert "Initech" in items[0]["title"]
    assert "3 days ago" in items[0]["detail"]


def test_recording_the_outcome_clears_the_reminder(client, registered_user):
    application = create_application(client, registered_user)
    interview = schedule(
        client, registered_user, application["id"], scheduled_at=iso(timedelta(days=-3))
    ).json()

    client.patch(
        f"/api/v1/interviews/{interview['id']}",
        headers=registered_user["headers"],
        json={"outcome": "passed"},
    )

    assert [
        i for i in reminders(client, registered_user) if i["kind"] == "interview_needs_outcome"
    ] == []


def test_a_wishlist_entry_going_quiet_is_not_a_reminder(client, registered_user, db_session):
    """Nothing was sent, so there is nothing to follow up."""
    application = create_application(client, registered_user, status="wishlist")
    _age(db_session, application["id"], days=40)

    assert [i for i in reminders(client, registered_user) if i["kind"] == "application_stale"] == []


def test_a_quiet_open_application_is_a_reminder(client, registered_user, db_session):
    application = create_application(client, registered_user, company_name="Hooli")
    _age(db_session, application["id"], days=30)

    items = [i for i in reminders(client, registered_user) if i["kind"] == "application_stale"]
    assert len(items) == 1
    assert "Hooli" in items[0]["title"]
    assert "30 days" in items[0]["detail"]
    assert items[0]["application_id"] == application["id"]


def test_a_closed_application_going_quiet_is_not_a_reminder(client, registered_user, db_session):
    application = create_application(client, registered_user, status="rejected")
    _age(db_session, application["id"], days=40)

    assert [i for i in reminders(client, registered_user) if i["kind"] == "application_stale"] == []


def test_overdue_reminders_come_before_upcoming_ones(client, registered_user):
    application = create_application(client, registered_user)
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=3)))
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=-2)))

    kinds = [i["kind"] for i in reminders(client, registered_user)]
    assert kinds.index("interview_needs_outcome") < kinds.index("interview_upcoming")


def test_reminders_are_scoped_to_the_owner(client, registered_user, other_user):
    application = create_application(client, registered_user)
    schedule(client, registered_user, application["id"], scheduled_at=iso(timedelta(days=-1)))

    assert reminders(client, other_user) == []


def _age(db_session, application_id: str, *, days: int) -> None:
    """Backdate updated_at, which onupdate would otherwise keep refreshing."""
    from sqlalchemy import text as sql_text

    db_session.execute(
        sql_text(
            "UPDATE applications SET updated_at = now() - make_interval(days => :d) WHERE id = :id"
        ),
        {"d": days, "id": application_id},
    )
    db_session.flush()
