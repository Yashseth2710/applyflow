"""Authentication endpoint tests."""

from fastapi.testclient import TestClient

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"

PASSWORD = "correct-horse-battery"


def _register_payload(email: str, **overrides: object) -> dict:
    payload = {
        "email": email,
        "password": PASSWORD,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "timezone": "Asia/Kolkata",
    }
    payload.update(overrides)
    return payload


class TestRegister:
    def test_creates_account_and_returns_token(self, client: TestClient, unique_email: str) -> None:
        r = client.post(REGISTER, json=_register_payload(unique_email))

        assert r.status_code == 201
        body = r.json()
        assert body["user"]["email"] == unique_email
        assert body["user"]["first_name"] == "Ada"
        assert body["token"]["access_token"]
        assert body["token"]["token_type"] == "bearer"

    def test_creates_profile_with_timezone(self, client: TestClient, unique_email: str) -> None:
        """A user without a profile is an invalid state."""
        r = client.post(REGISTER, json=_register_payload(unique_email, timezone="Europe/Berlin"))

        assert r.json()["user"]["profile"]["timezone"] == "Europe/Berlin"

    def test_unknown_timezone_falls_back_to_default(
        self, client: TestClient, unique_email: str
    ) -> None:
        r = client.post(
            REGISTER, json=_register_payload(unique_email, timezone="Mars/Olympus_Mons")
        )

        assert r.status_code == 201
        assert r.json()["user"]["profile"]["timezone"] == "Asia/Kolkata"

    def test_missing_timezone_falls_back_to_default(
        self, client: TestClient, unique_email: str
    ) -> None:
        payload = _register_payload(unique_email)
        del payload["timezone"]

        r = client.post(REGISTER, json=payload)

        assert r.json()["user"]["profile"]["timezone"] == "Asia/Kolkata"

    def test_never_returns_password_hash(self, client: TestClient, unique_email: str) -> None:
        r = client.post(REGISTER, json=_register_payload(unique_email))

        assert "password" not in r.text.lower()

    def test_sets_httponly_refresh_cookie(self, client: TestClient, unique_email: str) -> None:
        """The refresh token must be unreadable by JavaScript."""
        r = client.post(REGISTER, json=_register_payload(unique_email))

        # Starlette lowercases the attribute values, so compare case-insensitively.
        cookie_header = r.headers.get("set-cookie", "").lower()
        assert "applyflow_refresh=" in cookie_header
        assert "httponly" in cookie_header
        assert "samesite=lax" in cookie_header
        assert "path=/api/v1/auth" in cookie_header

    def test_duplicate_email_rejected(self, client: TestClient, unique_email: str) -> None:
        client.post(REGISTER, json=_register_payload(unique_email))

        r = client.post(REGISTER, json=_register_payload(unique_email))

        assert r.status_code == 409

    def test_email_is_case_insensitive(self, client: TestClient, unique_email: str) -> None:
        """Ada@x.com and ada@x.com must not become two accounts."""
        client.post(REGISTER, json=_register_payload(unique_email))

        r = client.post(REGISTER, json=_register_payload(unique_email.upper()))

        assert r.status_code == 409

    def test_short_password_rejected(self, client: TestClient, unique_email: str) -> None:
        r = client.post(REGISTER, json=_register_payload(unique_email, password="short"))

        assert r.status_code == 422

    def test_invalid_email_rejected(self, client: TestClient) -> None:
        r = client.post(REGISTER, json=_register_payload("not-an-email"))

        assert r.status_code == 422

    def test_blank_name_rejected(self, client: TestClient, unique_email: str) -> None:
        r = client.post(REGISTER, json=_register_payload(unique_email, first_name="   "))

        assert r.status_code == 422


class TestLogin:
    def test_succeeds_with_correct_credentials(
        self, client: TestClient, registered_user: dict
    ) -> None:
        r = client.post(LOGIN, json={"email": registered_user["email"], "password": PASSWORD})

        assert r.status_code == 200
        assert r.json()["token"]["access_token"]

    def test_works_with_different_email_casing(
        self, client: TestClient, registered_user: dict
    ) -> None:
        r = client.post(
            LOGIN,
            json={"email": registered_user["email"].upper(), "password": PASSWORD},
        )

        assert r.status_code == 200

    def test_wrong_password_rejected(self, client: TestClient, registered_user: dict) -> None:
        r = client.post(
            LOGIN, json={"email": registered_user["email"], "password": "wrong-password"}
        )

        assert r.status_code == 401

    def test_unknown_email_gives_identical_error(
        self, client: TestClient, registered_user: dict
    ) -> None:
        """Different messages would let an attacker enumerate registered emails."""
        wrong_pw = client.post(
            LOGIN, json={"email": registered_user["email"], "password": "wrong-password"}
        )
        no_user = client.post(
            LOGIN, json={"email": "nobody-here@example.com", "password": PASSWORD}
        )

        assert wrong_pw.status_code == no_user.status_code == 401
        assert wrong_pw.json()["detail"] == no_user.json()["detail"]


class TestMe:
    def test_returns_current_user(self, client: TestClient, registered_user: dict) -> None:
        r = client.get(ME, headers=registered_user["headers"])

        assert r.status_code == 200
        assert r.json()["email"] == registered_user["email"]

    def test_requires_authentication(self, client: TestClient) -> None:
        r = client.get(ME)

        assert r.status_code == 401

    def test_rejects_garbage_token(self, client: TestClient) -> None:
        r = client.get(ME, headers={"Authorization": "Bearer not-a-real-token"})

        assert r.status_code == 401

    def test_rejects_refresh_token_used_as_access_token(
        self, client: TestClient, unique_email: str
    ) -> None:
        """Token type is enforced. Otherwise a long-lived refresh token would
        work as an access token, defeating the short access lifetime."""
        reg = client.post(REGISTER, json=_register_payload(unique_email))
        refresh_cookie = client.cookies.get("applyflow_refresh")
        assert refresh_cookie, "expected a refresh cookie"
        assert reg.status_code == 201

        r = client.get(ME, headers={"Authorization": f"Bearer {refresh_cookie}"})

        assert r.status_code == 401

    def test_rejects_token_signed_with_wrong_secret(self, client: TestClient) -> None:
        import jwt

        forged = jwt.encode(
            {"sub": "00000000-0000-0000-0000-000000000000", "type": "access", "exp": 9999999999},
            "attacker-chosen-secret",
            algorithm="HS256",
        )

        r = client.get(ME, headers={"Authorization": f"Bearer {forged}"})

        assert r.status_code == 401


class TestRefresh:
    def test_issues_new_access_token(self, client: TestClient, registered_user: dict) -> None:
        r = client.post(REFRESH)

        assert r.status_code == 200
        assert r.json()["access_token"]

    def test_new_token_works(self, client: TestClient, registered_user: dict) -> None:
        token = client.post(REFRESH).json()["access_token"]

        r = client.get(ME, headers={"Authorization": f"Bearer {token}"})

        assert r.status_code == 200
        assert r.json()["email"] == registered_user["email"]

    def test_without_cookie_rejected(self, client: TestClient) -> None:
        client.cookies.clear()

        r = client.post(REFRESH)

        assert r.status_code == 401

    def test_invalid_cookie_rejected(self, client: TestClient) -> None:
        client.cookies.set("applyflow_refresh", "forged-token")

        r = client.post(REFRESH)

        assert r.status_code == 401


class TestLogout:
    def test_clears_cookie_and_blocks_refresh(
        self, client: TestClient, registered_user: dict
    ) -> None:
        assert client.post(LOGOUT).status_code == 204

        r = client.post(REFRESH)

        assert r.status_code == 401
