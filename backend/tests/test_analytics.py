"""Analytics: funnel arithmetic, the rate threshold, and access control."""

from fastapi.testclient import TestClient

from app.services.analytics import MIN_SAMPLE, MIN_SOURCE_SAMPLE


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


def move(client: TestClient, user: dict, application_id: str, status: str) -> None:
    """The dedicated status route, which is what writes history."""
    r = client.patch(
        f"/api/v1/applications/{application_id}/status",
        headers=user["headers"],
        json={"status": status},
    )
    assert r.status_code == 200, r.text


def summary(client: TestClient, user: dict) -> dict:
    r = client.get("/api/v1/analytics/summary", headers=user["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def step(body: dict, key: str) -> dict:
    return next(s for s in body["funnel"] if s["key"] == key)


# ---- access ----


def test_summary_requires_authentication(client):
    assert client.get("/api/v1/analytics/summary").status_code == 401


def test_summary_only_counts_your_own_applications(client, registered_user, other_user):
    for _ in range(3):
        create_application(client, other_user)

    body = summary(client, registered_user)
    assert body["totals"]["applications"] == 0
    assert step(body, "applied")["count"] == 0


# ---- empty ----


def test_empty_account_returns_zeros_not_an_error(client, registered_user):
    body = summary(client, registered_user)

    assert body["totals"]["applications"] == 0
    assert body["has_enough_data"] is False
    assert all(s["count"] == 0 for s in body["funnel"])
    assert body["statuses"] == []
    assert body["sources"] == []
    # The weekly series is generated, not derived from rows, so it exists even
    # when nothing has happened.
    assert len(body["volume"]) > 0
    assert all(point["created"] == 0 for point in body["volume"])


# ---- funnel ----


def test_funnel_counts_stages_an_application_has_left(client, registered_user):
    """Reaching the offer stage means every earlier rung was reached too, even
    though the application only sits in one of them."""
    application = create_application(client, registered_user)
    move(client, registered_user, application["id"], "technical_interview")
    move(client, registered_user, application["id"], "offer")

    body = summary(client, registered_user)

    assert step(body, "applied")["count"] == 1
    assert step(body, "interview")["count"] == 1
    assert step(body, "offer")["count"] == 1
    assert step(body, "accepted")["count"] == 0


def test_funnel_never_widens_further_down(client, registered_user):
    """A stage skipped on the way up must not leave a later rung larger than an
    earlier one — people log the interview they got, not the assessment."""
    application = create_application(client, registered_user)
    move(client, registered_user, application["id"], "final_interview")

    counts = [s["count"] for s in summary(client, registered_user)["funnel"]]
    assert counts == sorted(counts, reverse=True)
    # Assessment was never recorded, but the application clearly got past it.
    assert step(summary(client, registered_user), "assessment")["count"] == 1


def test_rejection_still_counts_towards_the_stage_it_reached(client, registered_user):
    application = create_application(client, registered_user)
    move(client, registered_user, application["id"], "technical_interview")
    move(client, registered_user, application["id"], "rejected")

    body = summary(client, registered_user)

    assert step(body, "interview")["count"] == 1
    assert body["totals"]["closed"] == 1
    assert body["totals"]["active"] == 0


def test_wishlist_entries_are_not_counted_as_applied(client, registered_user):
    create_application(client, registered_user, status="wishlist")

    body = summary(client, registered_user)

    assert body["totals"]["applications"] == 1
    assert body["totals"]["applied"] == 0
    assert step(body, "applied")["count"] == 0


# ---- the threshold on percentages ----


def test_rates_are_withheld_until_there_is_enough_data(client, registered_user):
    """One offer out of two applications is not a 50% offer rate."""
    for _ in range(MIN_SAMPLE - 1):
        create_application(client, registered_user)

    body = summary(client, registered_user)

    assert body["has_enough_data"] is False
    assert body["totals"]["offer_rate"] is None
    assert body["totals"]["response_rate"] is None
    assert all(s["rate"] is None for s in body["funnel"])
    # Counts are never withheld — they are honest at any volume.
    assert step(body, "applied")["count"] == MIN_SAMPLE - 1


def test_rates_appear_once_the_threshold_is_met(client, registered_user):
    applications = [create_application(client, registered_user) for _ in range(MIN_SAMPLE)]
    move(client, registered_user, applications[0]["id"], "offer")

    body = summary(client, registered_user)

    assert body["has_enough_data"] is True
    assert body["totals"]["offer_rate"] == round(1 / MIN_SAMPLE, 4)
    assert step(body, "applied")["rate"] == 1.0


def test_a_rejection_counts_as_having_heard_back(client, registered_user):
    applications = [create_application(client, registered_user) for _ in range(MIN_SAMPLE)]
    move(client, registered_user, applications[0]["id"], "rejected")

    body = summary(client, registered_user)

    # Silence is the thing being measured, and a "no" is not silence.
    assert body["totals"]["response_rate"] == round(1 / MIN_SAMPLE, 4)


# ---- sources ----


def test_sources_are_grouped_exactly_as_typed(client, registered_user):
    create_application(client, registered_user, source="LinkedIn")
    create_application(client, registered_user, source="linkedin")

    sources = {s["source"]: s["total"] for s in summary(client, registered_user)["sources"]}

    # Deliberately two rows: folding them together means guessing, and the
    # same guess would merge two genuinely different answers elsewhere.
    assert sources == {"LinkedIn": 1, "linkedin": 1}


def test_applications_without_a_source_are_grouped_under_nothing(client, registered_user):
    create_application(client, registered_user)

    sources = summary(client, registered_user)["sources"]

    assert len(sources) == 1
    assert sources[0]["source"] is None
    assert sources[0]["total"] == 1


def test_source_rate_needs_its_own_handful_of_applications(client, registered_user):
    for _ in range(MIN_SOURCE_SAMPLE - 1):
        create_application(client, registered_user, source="Referral")

    quiet = next(
        s for s in summary(client, registered_user)["sources"] if s["source"] == "Referral"
    )
    assert quiet["interview_rate"] is None

    create_application(client, registered_user, source="Referral")

    busy = next(s for s in summary(client, registered_user)["sources"] if s["source"] == "Referral")
    assert busy["total"] == MIN_SOURCE_SAMPLE
    assert busy["interview_rate"] == 0.0


def test_a_source_with_nothing_sent_has_no_rate(client, registered_user):
    """Three saved jobs from one board have not converted 0% of anything."""
    for _ in range(MIN_SOURCE_SAMPLE):
        create_application(client, registered_user, status="wishlist", source="LinkedIn")

    source = summary(client, registered_user)["sources"][0]

    assert source["total"] == MIN_SOURCE_SAMPLE
    assert source["sent"] == 0
    assert source["interview_rate"] is None


def test_sources_report_how_far_each_channel_gets(client, registered_user):
    for _ in range(MIN_SOURCE_SAMPLE):
        application = create_application(client, registered_user, source="Referral")
        move(client, registered_user, application["id"], "technical_interview")

    referral = next(
        s for s in summary(client, registered_user)["sources"] if s["source"] == "Referral"
    )
    assert referral["interviews"] == MIN_SOURCE_SAMPLE
    assert referral["interview_rate"] == 1.0
    assert referral["offers"] == 0


# ---- stages and timing ----


def test_stage_durations_only_count_stages_that_were_left(client, registered_user):
    application = create_application(client, registered_user)
    move(client, registered_user, application["id"], "assessment")

    durations = {d["status"]: d for d in summary(client, registered_user)["stage_durations"]}

    # "applied" was left, so it has a duration. "assessment" is where the
    # application still sits, and an unfinished stay is not a length.
    assert "applied" in durations
    assert durations["applied"]["moves"] == 1
    assert "assessment" not in durations


def test_response_median_is_withheld_on_thin_evidence(client, registered_user):
    application = create_application(client, registered_user)
    move(client, registered_user, application["id"], "assessment")

    totals = summary(client, registered_user)["totals"]

    assert totals["response_samples"] == 1
    assert totals["median_days_to_response"] is None


# ---- weekly volume ----


def test_volume_records_this_week(client, registered_user):
    application = create_application(client, registered_user)
    move(client, registered_user, application["id"], "assessment")

    body = summary(client, registered_user)
    latest = body["volume"][-1]

    assert latest["created"] == 1
    # One move, not two — the entry written when the application was created
    # is not a stage change.
    assert latest["moved"] == 1


def test_volume_covers_a_fixed_window_of_weeks(client, registered_user):
    volume = summary(client, registered_user)["volume"]

    weeks = [point["week_start"] for point in volume]
    assert weeks == sorted(weeks)
    assert len(set(weeks)) == len(weeks)
