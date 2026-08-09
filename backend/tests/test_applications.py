"""Application endpoint tests."""

import uuid

from fastapi.testclient import TestClient

BASE = "/api/v1/applications"


def _payload(**overrides: object) -> dict:
    payload: dict = {
        "company_name": "Acme Corp",
        "job_title": "Backend Engineer",
        "location": "Bengaluru",
        "work_mode": "hybrid",
        "employment_type": "full_time",
        "salary_min": 1_200_000,
        "salary_max": 1_800_000,
        "source": "LinkedIn",
    }
    payload.update(overrides)
    return payload


def _create(client: TestClient, user: dict, **overrides: object) -> dict:
    r = client.post(BASE, json=_payload(**overrides), headers=user["headers"])
    assert r.status_code == 201, r.text
    return r.json()


class TestCreate:
    def test_creates_application(self, client: TestClient, registered_user: dict) -> None:
        r = client.post(BASE, json=_payload(), headers=registered_user["headers"])

        assert r.status_code == 201
        body = r.json()
        assert body["company_name"] == "Acme Corp"
        assert body["job_title"] == "Backend Engineer"
        assert body["status"] == "wishlist"
        assert body["salary_currency"] == "INR"

    def test_records_initial_history_entry(self, client: TestClient, registered_user: dict) -> None:
        """The journey is unrecoverable if the starting point isn't captured."""
        body = _create(client, registered_user)

        assert len(body["status_history"]) == 1
        assert body["status_history"][0]["from_status"] is None
        assert body["status_history"][0]["to_status"] == "wishlist"

    def test_wishlist_does_not_set_date_applied(
        self, client: TestClient, registered_user: dict
    ) -> None:
        body = _create(client, registered_user)

        assert body["date_applied"] is None

    def test_creating_as_applied_stamps_date_applied(
        self, client: TestClient, registered_user: dict
    ) -> None:
        body = _create(client, registered_user, status="applied")

        assert body["date_applied"] is not None

    def test_requires_authentication(self, client: TestClient) -> None:
        r = client.post(BASE, json=_payload())

        assert r.status_code == 401

    def test_blank_company_rejected(self, client: TestClient, registered_user: dict) -> None:
        r = client.post(BASE, json=_payload(company_name="   "), headers=registered_user["headers"])

        assert r.status_code == 422

    def test_inverted_salary_range_rejected(
        self, client: TestClient, registered_user: dict
    ) -> None:
        """Caught in the schema so the user gets a clear 422 rather than a 500
        from the database CHECK constraint."""
        r = client.post(
            BASE,
            json=_payload(salary_min=2_000_000, salary_max=1_000_000),
            headers=registered_user["headers"],
        )

        assert r.status_code == 422

    def test_empty_strings_become_null(self, client: TestClient, registered_user: dict) -> None:
        """ "No value" should have one representation, not two."""
        body = _create(client, registered_user, location="", source="  ")

        assert body["location"] is None
        assert body["source"] is None


class TestList:
    def test_lists_only_own_applications(
        self, client: TestClient, registered_user: dict, other_user: dict
    ) -> None:
        _create(client, registered_user, company_name="Mine")
        _create(client, other_user, company_name="Theirs")

        r = client.get(BASE, headers=registered_user["headers"])

        names = [i["company_name"] for i in r.json()["items"]]
        assert names == ["Mine"]

    def test_pagination(self, client: TestClient, registered_user: dict) -> None:
        for i in range(5):
            _create(client, registered_user, company_name=f"Company {i}")

        r = client.get(f"{BASE}?page=1&page_size=2", headers=registered_user["headers"])

        body = r.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["pages"] == 3

    def test_filter_by_status(self, client: TestClient, registered_user: dict) -> None:
        _create(client, registered_user, company_name="A", status="applied")
        _create(client, registered_user, company_name="B", status="wishlist")

        r = client.get(f"{BASE}?status=applied", headers=registered_user["headers"])

        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["company_name"] == "A"

    def test_search_matches_partial_company_name(
        self, client: TestClient, registered_user: dict
    ) -> None:
        _create(client, registered_user, company_name="Google India")
        _create(client, registered_user, company_name="Microsoft")

        r = client.get(f"{BASE}?search=goog", headers=registered_user["headers"])

        assert [i["company_name"] for i in r.json()["items"]] == ["Google India"]

    def test_search_matches_job_title(self, client: TestClient, registered_user: dict) -> None:
        _create(client, registered_user, company_name="A", job_title="Data Scientist")
        _create(client, registered_user, company_name="B", job_title="Backend Engineer")

        r = client.get(f"{BASE}?search=scientist", headers=registered_user["headers"])

        assert [i["company_name"] for i in r.json()["items"]] == ["A"]

    def test_sort_by_company_name(self, client: TestClient, registered_user: dict) -> None:
        _create(client, registered_user, company_name="Zeta")
        _create(client, registered_user, company_name="Alpha")

        r = client.get(f"{BASE}?sort_by=company_name&order=asc", headers=registered_user["headers"])

        assert [i["company_name"] for i in r.json()["items"]] == ["Alpha", "Zeta"]

    def test_page_size_capped(self, client: TestClient, registered_user: dict) -> None:
        r = client.get(f"{BASE}?page_size=5000", headers=registered_user["headers"])

        assert r.status_code == 422


class TestGet:
    def test_returns_application_with_history(
        self, client: TestClient, registered_user: dict
    ) -> None:
        created = _create(client, registered_user)

        r = client.get(f"{BASE}/{created['id']}", headers=registered_user["headers"])

        assert r.status_code == 200
        assert r.json()["id"] == created["id"]
        assert len(r.json()["status_history"]) == 1

    def test_unknown_id_404(self, client: TestClient, registered_user: dict) -> None:
        r = client.get(f"{BASE}/{uuid.uuid4()}", headers=registered_user["headers"])

        assert r.status_code == 404

    def test_other_users_application_is_404_not_403(
        self, client: TestClient, registered_user: dict, other_user: dict
    ) -> None:
        """403 would confirm the id exists, letting an attacker enumerate records."""
        theirs = _create(client, other_user)

        r = client.get(f"{BASE}/{theirs['id']}", headers=registered_user["headers"])

        assert r.status_code == 404


class TestUpdate:
    def test_updates_supplied_fields_only(self, client: TestClient, registered_user: dict) -> None:
        created = _create(client, registered_user)

        r = client.patch(
            f"{BASE}/{created['id']}",
            json={"job_title": "Senior Backend Engineer"},
            headers=registered_user["headers"],
        )

        body = r.json()
        assert body["job_title"] == "Senior Backend Engineer"
        assert body["company_name"] == "Acme Corp"  # untouched
        assert body["location"] == "Bengaluru"

    def test_cannot_change_status_via_patch(
        self, client: TestClient, registered_user: dict
    ) -> None:
        """Status must go through /status so the change is recorded in history."""
        created = _create(client, registered_user)

        r = client.patch(
            f"{BASE}/{created['id']}",
            json={"status": "offer"},
            headers=registered_user["headers"],
        )

        assert r.status_code == 422

    def test_other_users_application_is_404(
        self, client: TestClient, registered_user: dict, other_user: dict
    ) -> None:
        theirs = _create(client, other_user)

        r = client.patch(
            f"{BASE}/{theirs['id']}",
            json={"job_title": "Hijacked"},
            headers=registered_user["headers"],
        )

        assert r.status_code == 404


class TestStatusChange:
    def test_changes_status(self, client: TestClient, registered_user: dict) -> None:
        created = _create(client, registered_user)

        r = client.patch(
            f"{BASE}/{created['id']}/status",
            json={"status": "technical_interview"},
            headers=registered_user["headers"],
        )

        assert r.status_code == 200
        assert r.json()["status"] == "technical_interview"

    def test_writes_history_entry(self, client: TestClient, registered_user: dict) -> None:
        created = _create(client, registered_user)

        client.patch(
            f"{BASE}/{created['id']}/status",
            json={"status": "applied"},
            headers=registered_user["headers"],
        )
        detail = client.get(f"{BASE}/{created['id']}", headers=registered_user["headers"]).json()

        assert len(detail["status_history"]) == 2
        assert detail["status_history"][1]["from_status"] == "wishlist"
        assert detail["status_history"][1]["to_status"] == "applied"

    def test_same_status_writes_no_history(self, client: TestClient, registered_user: dict) -> None:
        """A drag landing a card back in its own column is not a transition;
        logging it would skew time-in-stage."""
        created = _create(client, registered_user)

        client.patch(
            f"{BASE}/{created['id']}/status",
            json={"status": "wishlist", "position": 3},
            headers=registered_user["headers"],
        )
        detail = client.get(f"{BASE}/{created['id']}", headers=registered_user["headers"]).json()

        assert len(detail["status_history"]) == 1

    def test_moving_out_of_wishlist_stamps_date_applied(
        self, client: TestClient, registered_user: dict
    ) -> None:
        created = _create(client, registered_user)
        assert created["date_applied"] is None

        r = client.patch(
            f"{BASE}/{created['id']}/status",
            json={"status": "applied"},
            headers=registered_user["headers"],
        )

        assert r.json()["date_applied"] is not None

    def test_position_is_applied(self, client: TestClient, registered_user: dict) -> None:
        created = _create(client, registered_user)

        r = client.patch(
            f"{BASE}/{created['id']}/status",
            json={"status": "offer", "position": 7},
            headers=registered_user["headers"],
        )

        assert r.json()["position"] == 7

    def test_invalid_status_rejected(self, client: TestClient, registered_user: dict) -> None:
        created = _create(client, registered_user)

        r = client.patch(
            f"{BASE}/{created['id']}/status",
            json={"status": "definitely_not_a_status"},
            headers=registered_user["headers"],
        )

        assert r.status_code == 422

    def test_other_users_application_is_404(
        self, client: TestClient, registered_user: dict, other_user: dict
    ) -> None:
        theirs = _create(client, other_user)

        r = client.patch(
            f"{BASE}/{theirs['id']}/status",
            json={"status": "rejected"},
            headers=registered_user["headers"],
        )

        assert r.status_code == 404


class TestDelete:
    def test_deletes(self, client: TestClient, registered_user: dict) -> None:
        created = _create(client, registered_user)

        assert (
            client.delete(f"{BASE}/{created['id']}", headers=registered_user["headers"]).status_code
            == 204
        )
        assert (
            client.get(f"{BASE}/{created['id']}", headers=registered_user["headers"]).status_code
            == 404
        )

    def test_other_users_application_is_404(
        self, client: TestClient, registered_user: dict, other_user: dict
    ) -> None:
        theirs = _create(client, other_user)

        r = client.delete(f"{BASE}/{theirs['id']}", headers=registered_user["headers"])

        assert r.status_code == 404

        # And it must still be there.
        still = client.get(f"{BASE}/{theirs['id']}", headers=other_user["headers"])
        assert still.status_code == 200


class TestBoard:
    def test_returns_every_status_column(self, client: TestClient, registered_user: dict) -> None:
        r = client.get(f"{BASE}/board", headers=registered_user["headers"])

        assert r.status_code == 200
        assert len(r.json()["columns"]) == 12

    def test_groups_applications_by_status(self, client: TestClient, registered_user: dict) -> None:
        _create(client, registered_user, company_name="A", status="applied")
        _create(client, registered_user, company_name="B", status="applied")
        _create(client, registered_user, company_name="C", status="offer")

        body = client.get(f"{BASE}/board", headers=registered_user["headers"]).json()
        columns = {c["status"]: c for c in body["columns"]}

        assert body["total"] == 3
        assert columns["applied"]["count"] == 2
        assert columns["offer"]["count"] == 1
        assert columns["rejected"]["count"] == 0

    def test_excludes_other_users(
        self, client: TestClient, registered_user: dict, other_user: dict
    ) -> None:
        _create(client, other_user, company_name="Theirs")

        body = client.get(f"{BASE}/board", headers=registered_user["headers"]).json()

        assert body["total"] == 0

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(f"{BASE}/board").status_code == 401


class TestSources:
    def test_lists_distinct_sources(self, client: TestClient, registered_user: dict) -> None:
        _create(client, registered_user, company_name="A", source="LinkedIn")
        _create(client, registered_user, company_name="B", source="LinkedIn")
        _create(client, registered_user, company_name="C", source="Referral")

        r = client.get(f"{BASE}/sources", headers=registered_user["headers"])

        assert sorted(r.json()) == ["LinkedIn", "Referral"]

    def test_excludes_other_users_sources(
        self, client: TestClient, registered_user: dict, other_user: dict
    ) -> None:
        _create(client, other_user, source="SecretJobBoard")

        r = client.get(f"{BASE}/sources", headers=registered_user["headers"])

        assert "SecretJobBoard" not in r.json()
