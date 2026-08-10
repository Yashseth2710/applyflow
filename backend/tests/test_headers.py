"""Security response headers.

Headers are the kind of thing that gets added once, silently dropped by a
refactor, and never noticed — nothing breaks when they go missing. These tests
are the only thing that would notice.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.headers import HSTS

HEALTH = "/api/v1/health"


def test_json_cannot_be_sniffed_as_something_else(client: TestClient) -> None:
    assert client.get(HEALTH).headers["X-Content-Type-Options"] == "nosniff"


def test_the_api_cannot_be_framed(client: TestClient) -> None:
    """Both spellings: frame-ancestors for browsers that read CSP, and
    X-Frame-Options for the ones that do not."""
    headers = client.get(HEALTH).headers

    assert headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


def test_the_api_may_load_nothing_at_all(client: TestClient) -> None:
    """It answers in JSON. There is no legitimate reason for a response from
    here to pull in a script, a stylesheet or an image."""
    assert client.get(HEALTH).headers["Content-Security-Policy"].startswith("default-src 'none'")


def test_full_urls_are_not_handed_to_other_sites(client: TestClient) -> None:
    """A password reset link lives in a URL, and a full referrer is how such a
    link ends up in a stranger's access log."""
    assert client.get(HEALTH).headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_nothing_may_ask_for_a_camera(client: TestClient) -> None:
    policy = client.get(HEALTH).headers["Permissions-Policy"]

    for feature in ("camera=()", "microphone=()", "geolocation=()"):
        assert feature in policy


def test_headers_survive_an_error_response(client: TestClient) -> None:
    """A 404 is still a response a browser will act on, and the error paths are
    exactly where middleware tends to be skipped."""
    headers = client.get("/api/v1/no-such-endpoint").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_no_hsts_in_development(client: TestClient) -> None:
    """Sent over plain-HTTP localhost it would pin every project on the
    machine's localhost to HTTPS, in a way that is genuinely awkward to undo."""
    assert "Strict-Transport-Security" not in client.get(HEALTH).headers


def test_hsts_in_production_behind_the_proxy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The host terminates TLS, so the request arrives as plain http and only
    x-forwarded-proto says otherwise. Reading the scheme alone would mean never
    sending HSTS at all."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    r = client.get(HEALTH, headers={"x-forwarded-proto": "https"})

    assert r.headers["Strict-Transport-Security"] == HSTS


def test_no_hsts_over_plain_http_even_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    assert "Strict-Transport-Security" not in client.get(HEALTH).headers
