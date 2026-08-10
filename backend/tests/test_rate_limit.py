"""Rate limiting.

These tests switch the limiter back on for themselves — the suite runs with it
off, because every request comes from one address.
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.rate_limit import account_or_ip, client_ip, limiter
from app.core.security import create_access_token


@pytest.fixture
def limited() -> Generator[None, None, None]:
    """Limits on, counters empty, for one test."""
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.enabled = False
    limiter.reset()


def _register_payload() -> dict:
    return {
        "email": f"rl-{uuid.uuid4().hex[:12]}@example.com",
        "password": "correct-horse-battery",
        "first_name": "Test",
        "last_name": "User",
        "timezone": "Asia/Kolkata",
    }


def test_registration_stops_after_the_allowance(client: TestClient, limited: None) -> None:
    codes = [
        client.post("/api/v1/auth/register", json=_register_payload()).status_code for _ in range(6)
    ]

    assert codes[:5] == [201] * 5
    assert codes[5] == 429


def test_a_blocked_request_says_when_to_come_back(client: TestClient, limited: None) -> None:
    for _ in range(5):
        client.post("/api/v1/auth/register", json=_register_payload())

    r = client.post("/api/v1/auth/register", json=_register_payload())

    assert r.status_code == 429
    # The client shows a wait, so the body has to parse like every other error
    # and the header has to be there to read.
    assert r.json() == {"detail": "Too many requests. Try again in a moment."}
    assert int(r.headers["Retry-After"]) > 0


def test_wrong_passwords_stop_being_answered(client: TestClient, limited: None) -> None:
    """The point of the exercise: guessing has to become pointless."""
    payload = {"email": "someone@example.com", "password": "wrong"}

    codes = [client.post("/api/v1/auth/login", json=payload).status_code for _ in range(11)]

    # Ten wrong answers, then the eleventh is not even checked.
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_a_failed_login_still_costs_an_attempt(
    client: TestClient, registered_user: dict, limited: None
) -> None:
    """A limit that only counted successes would not slow a guesser down."""
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": "wrong"},
        )

    r = client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert r.status_code == 429


def test_reading_data_is_not_limited(
    client: TestClient, registered_user: dict, limited: None
) -> None:
    """Only the expensive and guessable routes are capped. A list endpoint
    being throttled would break normal use for no security gain."""
    codes = [
        client.get("/api/v1/applications", headers=registered_user["headers"]).status_code
        for _ in range(30)
    ]

    assert set(codes) == {200}


class _Request:
    """Enough of a Request for the key functions."""

    def __init__(self, headers: dict[str, str], host: str | None = "203.0.113.9"):
        self.headers = headers
        self.client = type("C", (), {"host": host})() if host else None
        self.scope: dict = {}


def test_the_address_comes_from_the_socket_when_nothing_is_in_front(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 0)

    # A header nobody asked for is ignored, which is what stops a caller
    # handing themselves a fresh allowance per request.
    request = _Request({"x-forwarded-for": "1.1.1.1"}, host="203.0.113.9")

    assert client_ip(request) == "203.0.113.9"  # type: ignore[arg-type]


def test_one_proxy_in_front_reads_the_entry_it_appended(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 1)

    # The client wrote the first entry itself; the proxy appended the real one.
    # Believing the left-hand end would let anyone spoof their way past the cap.
    request = _Request({"x-forwarded-for": "10.0.0.1, 198.51.100.7"})

    assert client_ip(request) == "198.51.100.7"  # type: ignore[arg-type]


def test_a_short_chain_falls_back_rather_than_trusting_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fewer entries than expected means the request did not come through the
    proxy, so nothing in the header was written by anyone trustworthy."""
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 2)

    request = _Request({"x-forwarded-for": "10.0.0.1"}, host="203.0.113.9")

    assert client_ip(request) == "203.0.113.9"  # type: ignore[arg-type]


def test_the_ai_allowance_follows_the_account() -> None:
    user_id = str(uuid.uuid4())
    first = _Request({"authorization": f"Bearer {create_access_token(user_id)}"})
    # A second token for the same person — they rotate every fifteen minutes,
    # and keying on the string would hand out a clean slate on every refresh.
    second = _Request({"authorization": f"Bearer {create_access_token(user_id)}"})

    assert account_or_ip(first) == account_or_ip(second)  # type: ignore[arg-type]
    assert account_or_ip(first) == f"user:{user_id}"  # type: ignore[arg-type]


def test_an_unusable_token_falls_back_to_the_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Otherwise sending rubbish in the header would be a way past the limit."""
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 0)

    request = _Request({"authorization": "Bearer not-a-token"})

    assert account_or_ip(request) == "ip:203.0.113.9"  # type: ignore[arg-type]


def test_one_ipv6_customer_is_one_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    """A home IPv6 line is handed a whole /64. Counting the full address means
    a fresh allowance for every request, which is not a limit at all."""
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 1)

    def bucket_for(address: str) -> str:
        return client_ip(_Request({"x-forwarded-for": address}))  # type: ignore[arg-type]

    first = bucket_for("2001:db8:1234:5678::1")
    # Same customer, a different address out of the same allocation.
    second = bucket_for("2001:db8:1234:5678:abcd:ef01:2345:6789")

    assert first == second == "2001:db8:1234:5678::/64"


def test_a_different_ipv6_allocation_is_a_different_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 1)

    mine = client_ip(_Request({"x-forwarded-for": "2001:db8:1111:2222::5"}))  # type: ignore[arg-type]
    theirs = client_ip(_Request({"x-forwarded-for": "2001:db8:3333:4444::5"}))  # type: ignore[arg-type]

    assert mine != theirs


def test_ipv4_is_left_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """No equivalent problem: one IPv4 address is one caller."""
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 1)

    assert client_ip(_Request({"x-forwarded-for": "198.51.100.7"})) == "198.51.100.7"  # type: ignore[arg-type]


def test_an_unparseable_address_still_gets_a_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dropping the cap for callers sending nonsense would be exactly backwards."""
    monkeypatch.setattr("app.core.rate_limit.settings.RATE_LIMIT_PROXY_DEPTH", 1)

    assert client_ip(_Request({"x-forwarded-for": "not-an-address"})) == "not-an-address"  # type: ignore[arg-type]


def test_production_refuses_to_start_without_a_deliberate_proxy_depth() -> None:
    """The default is right locally and harmful behind a proxy, and the damage
    is invisible until someone is already locked out. Better to not start."""
    with pytest.raises(ValidationError, match="RATE_LIMIT_PROXY_DEPTH"):
        Settings(
            DATABASE_URL="postgresql://u:p@localhost/db",
            JWT_SECRET="x" * 40,
            ENVIRONMENT="production",
            _env_file=None,
        )


def test_production_is_happy_once_it_is_set() -> None:
    """Including setting it to 0 — the objection is to inheriting the default
    without having thought about it, not to the value itself."""
    for depth in (0, 1):
        settings_ = Settings(
            DATABASE_URL="postgresql://u:p@localhost/db",
            JWT_SECRET="x" * 40,
            ENVIRONMENT="production",
            RATE_LIMIT_PROXY_DEPTH=depth,
            _env_file=None,
        )
        assert depth == settings_.RATE_LIMIT_PROXY_DEPTH


def test_development_keeps_the_default() -> None:
    """Nobody running this locally should have to think about proxies."""
    settings_ = Settings(
        DATABASE_URL="postgresql://u:p@localhost/db",
        JWT_SECRET="x" * 40,
        _env_file=None,
    )

    assert settings_.RATE_LIMIT_PROXY_DEPTH == 0
