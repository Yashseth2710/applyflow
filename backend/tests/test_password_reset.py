"""Forgotten passwords.

The interesting cases here are not the happy path — they are the ones where the
endpoint has to say nothing useful: an address with no account, a link that has
already been used, a link someone made up.
"""

import re
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints import auth as auth_endpoints
from app.core.config import settings
from app.core.security import create_access_token, create_reset_token
from app.models.user import User

FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
LOGIN = "/api/v1/auth/login"

NEW_PASSWORD = "a-completely-different-one"


class Outbox(list):
    """Every message the endpoint asked to have sent."""

    def link(self) -> str:
        assert self, "nothing was sent"
        match = re.search(r"https?://\S+", self[-1]["body"])
        assert match, f"no link in the email:\n{self[-1]['body']}"
        return match.group(0)

    def token(self) -> str:
        return self.link().split("token=", 1)[1]


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    """Intercepts the send so the tests can read the link out of the mail.

    Patched at the endpoint rather than inside the mailer, so the background
    task and its arguments are exercised too.
    """
    sent = Outbox()

    def fake_send(*, to: str, subject: str, body: str) -> None:
        sent.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr(auth_endpoints, "send_email", fake_send)
    return sent


@pytest.fixture
def short_login_limit(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Two failed sign-ins instead of ten, so the lockout test stays quick."""
    monkeypatch.setattr(settings, "LOGIN_ATTEMPT_LIMIT", 2)
    yield


class TestRequestingALink:
    def test_sends_a_link_to_a_registered_address(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        r = client.post(FORGOT, json={"email": registered_user["email"]})

        assert r.status_code == 204
        assert len(outbox) == 1
        assert outbox[0]["to"] == registered_user["email"]
        assert outbox.link().startswith(settings.FRONTEND_URL)
        assert "/reset-password?token=" in outbox.link()

    def test_says_nothing_about_addresses_with_no_account(
        self, client: TestClient, outbox: Outbox
    ) -> None:
        """Same status, same empty body, and no mail. Any difference here would
        turn the endpoint into a way to test whether someone has an account."""
        r = client.post(FORGOT, json={"email": "nobody-at-all@example.com"})

        assert r.status_code == 204
        assert r.content == b""
        assert outbox == []

    def test_the_address_is_matched_regardless_of_case(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        r = client.post(FORGOT, json={"email": registered_user["email"].upper()})

        assert r.status_code == 204
        assert len(outbox) == 1

    def test_a_malformed_address_is_rejected(self, client: TestClient) -> None:
        assert client.post(FORGOT, json={"email": "not-an-address"}).status_code == 422

    def test_the_password_is_not_in_the_email(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        """The original plan was to mail a new password. It became a link
        precisely so that nothing usable travels in the message."""
        client.post(FORGOT, json={"email": registered_user["email"]})

        assert registered_user["password"] not in outbox[0]["body"]

    def test_only_so_many_emails_to_one_address(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        """Durable, and keyed on the address being mailed rather than the
        caller's, because the person who suffers is whoever owns the inbox."""
        codes = [
            client.post(FORGOT, json={"email": registered_user["email"]}).status_code
            for _ in range(settings.PASSWORD_RESET_HOURLY_LIMIT + 1)
        ]

        assert codes[:-1] == [204] * settings.PASSWORD_RESET_HOURLY_LIMIT
        assert codes[-1] == 429
        assert len(outbox) == settings.PASSWORD_RESET_HOURLY_LIMIT

    def test_unknown_addresses_use_up_the_same_allowance(
        self, client: TestClient, outbox: Outbox
    ) -> None:
        """Otherwise the 429 answers the question the 204 refuses to: a limit
        that only applied to real accounts would identify them."""
        address = "still-nobody@example.com"
        codes = [
            client.post(FORGOT, json={"email": address}).status_code
            for _ in range(settings.PASSWORD_RESET_HOURLY_LIMIT + 1)
        ]

        assert codes[-1] == 429


class TestUsingTheLink:
    def test_sets_the_new_password(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        client.post(FORGOT, json={"email": registered_user["email"]})

        r = client.post(RESET, json={"token": outbox.token(), "password": NEW_PASSWORD})
        assert r.status_code == 204

        after = client.post(
            LOGIN, json={"email": registered_user["email"], "password": NEW_PASSWORD}
        )
        assert after.status_code == 200

    def test_the_old_password_stops_working(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        client.post(FORGOT, json={"email": registered_user["email"]})
        client.post(RESET, json={"token": outbox.token(), "password": NEW_PASSWORD})

        r = client.post(
            LOGIN, json={"email": registered_user["email"], "password": registered_user["password"]}
        )
        assert r.status_code == 401

    def test_does_not_hand_back_a_session(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        """A link from an email is weaker evidence than a password. The reset
        finishes at the login page, not signed in."""
        client.post(FORGOT, json={"email": registered_user["email"]})

        r = client.post(RESET, json={"token": outbox.token(), "password": NEW_PASSWORD})

        assert r.content == b""
        assert "applyflow_refresh" not in r.cookies

    def test_a_link_only_works_once(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        """No table records that it was used. Using it changes the password
        hash, and the token carries a fingerprint of the old one."""
        client.post(FORGOT, json={"email": registered_user["email"]})
        token = outbox.token()

        first = client.post(RESET, json={"token": token, "password": NEW_PASSWORD})
        assert first.status_code == 204

        again = client.post(RESET, json={"token": token, "password": "yet-another-password"})
        assert again.status_code == 400

    def test_an_earlier_link_dies_when_a_later_one_is_used(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        client.post(FORGOT, json={"email": registered_user["email"]})
        earlier = outbox.token()
        client.post(FORGOT, json={"email": registered_user["email"]})
        later = outbox.token()

        used = client.post(RESET, json={"token": later, "password": NEW_PASSWORD})
        assert used.status_code == 204

        stale = client.post(RESET, json={"token": earlier, "password": NEW_PASSWORD})
        assert stale.status_code == 400

    def test_changing_the_password_from_settings_kills_an_outstanding_link(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        client.post(FORGOT, json={"email": registered_user["email"]})
        token = outbox.token()

        changed = client.post(
            "/api/v1/users/me/password",
            headers=registered_user["headers"],
            json={"current_password": registered_user["password"], "new_password": NEW_PASSWORD},
        )
        assert changed.status_code == 204

        assert (
            client.post(RESET, json={"token": token, "password": "third-password"}).status_code
            == 400
        )

    def test_an_expired_link_is_refused(
        self,
        client: TestClient,
        registered_user: dict,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "PASSWORD_RESET_EXPIRE_MINUTES", -1)
        user = db_session.get(User, registered_user["id"])
        assert user is not None
        token = create_reset_token(str(user.id), user.password_hash)

        r = client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

        assert r.status_code == 400

    def test_an_access_token_is_not_a_reset_token(
        self, client: TestClient, registered_user: dict
    ) -> None:
        """Otherwise anything holding a session could set a new password without
        knowing the current one, which is the check the settings page makes."""
        token = create_access_token(registered_user["id"])

        r = client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

        assert r.status_code == 400

    def test_a_made_up_token_is_refused(self, client: TestClient) -> None:
        r = client.post(RESET, json={"token": "not.a.jwt", "password": NEW_PASSWORD})

        assert r.status_code == 400

    def test_the_new_password_still_has_to_be_long_enough(
        self, client: TestClient, registered_user: dict, outbox: Outbox
    ) -> None:
        client.post(FORGOT, json={"email": registered_user["email"]})

        r = client.post(RESET, json={"token": outbox.token(), "password": "short"})

        assert r.status_code == 422

    def test_resetting_ends_the_lockout(
        self,
        client: TestClient,
        registered_user: dict,
        outbox: Outbox,
        short_login_limit: None,
    ) -> None:
        """The failed attempts are what sent them here. Leaving the account
        locked after a successful reset would be a dead end."""
        for _ in range(settings.LOGIN_ATTEMPT_LIMIT):
            client.post(LOGIN, json={"email": registered_user["email"], "password": "wrong"})

        locked = client.post(
            LOGIN, json={"email": registered_user["email"], "password": registered_user["password"]}
        )
        assert locked.status_code == 429

        client.post(FORGOT, json={"email": registered_user["email"]})
        assert (
            client.post(RESET, json={"token": outbox.token(), "password": NEW_PASSWORD}).status_code
            == 204
        )

        after = client.post(
            LOGIN, json={"email": registered_user["email"], "password": NEW_PASSWORD}
        )
        assert after.status_code == 200
