"""Health endpoint tests."""

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app


def test_health_returns_ok_with_live_database(client: TestClient) -> None:
    """Hits the real database — this is an integration test by design.

    The point of the health check is proving connectivity, so mocking it away
    would test nothing worth testing.
    """
    r = client.get("/api/v1/health")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"]["connected"] is True
    assert body["database"]["latency_ms"] > 0
    assert body["database"]["error"] is None
    assert body["version"]


def test_health_reports_degraded_when_database_is_down(client: TestClient) -> None:
    """A failing database must produce 503, not a cheerful 200."""

    def broken_db():
        class BrokenSession:
            def execute(self, *args, **kwargs):
                raise OperationalError("SELECT 1", {}, Exception("connection refused"))

            def close(self) -> None:
                pass

        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        r = client.get("/api/v1/health")

        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "degraded"
        assert body["database"]["connected"] is False
        assert body["database"]["latency_ms"] is None
    finally:
        app.dependency_overrides.clear()


def test_health_error_does_not_leak_connection_details(client: TestClient) -> None:
    """Failure messages must not expose credentials or host names."""

    def broken_db():
        class BrokenSession:
            def execute(self, *args, **kwargs):
                raise OperationalError(
                    "SELECT 1",
                    {},
                    Exception("password authentication failed for user 'neondb_owner'"),
                )

            def close(self) -> None:
                pass

        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        body = client.get("/api/v1/health").json()
        leaked = body["database"]["error"]

        assert leaked == "database unreachable"
        assert "neondb_owner" not in str(body)
        assert "password" not in str(body).lower()
    finally:
        app.dependency_overrides.clear()


def test_root_endpoint(client: TestClient) -> None:
    r = client.get("/")

    assert r.status_code == 200
    assert r.json()["name"] == "ApplyFlow"
