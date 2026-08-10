"""Shared test fixtures."""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_ai_provider
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.rate_limit import limiter
from app.main import app
from app.services.ai import MockProvider


@pytest.fixture(autouse=True)
def _no_real_email(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may send mail, whatever is in the developer's .env.

    Pinned the same way the AI provider is: once someone configures SMTP
    locally, a test that asks for a password reset stops being a test and
    starts delivering to a real inbox. With no host the message is logged
    instead, which is what every assertion here expects anyway.
    """
    monkeypatch.setattr(settings, "SMTP_HOST", "")


@pytest.fixture(autouse=True)
def _no_rate_limits() -> Generator[None, None, None]:
    """Rate limiting off unless a test asks for it.

    Every request in the suite arrives from the same address, so the limits
    would fire partway through a run and the failure would land on whichever
    test happened to be next rather than the one that caused it.
    `test_rate_limit.py` turns it back on for itself.
    """
    limiter.enabled = False
    limiter.reset()
    yield
    limiter.enabled = False
    limiter.reset()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """A session whose writes are always rolled back.

    Each test runs inside an outer transaction that is discarded at the end, so
    tests can create real users without leaving rows behind. `join_transaction_mode
    ="create_savepoint"` means the service layer's own `commit()` calls only
    release a savepoint rather than committing for real.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient wired to the rollback session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Pinned for every test: without this a developer's AI_PROVIDER setting
    # would decide whether the suite called a live API and burned real quota.
    app.dependency_overrides[get_ai_provider] = MockProvider
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    """Unique per test, so a leaked row can never collide with a later run."""
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def _register(client: TestClient, email: str) -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery",
            "first_name": "Test",
            "last_name": "User",
            "timezone": "Asia/Kolkata",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return {
        "email": email,
        "password": "correct-horse-battery",
        "id": body["user"]["id"],
        "access_token": body["token"]["access_token"],
        "headers": {"Authorization": f"Bearer {body['token']['access_token']}"},
    }


@pytest.fixture
def other_user(client: TestClient) -> dict:
    """A second account, for proving one user cannot reach another's data."""
    user = _register(client, f"other-{uuid.uuid4().hex[:12]}@example.com")
    # Registering logs this client in as the second user; drop the cookies so
    # the primary user's fixtures aren't affected by the switch.
    client.cookies.clear()
    return user


@pytest.fixture
def registered_user(client: TestClient, unique_email: str) -> dict:
    """A registered account plus its access token."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "correct-horse-battery",
            "first_name": "Test",
            "last_name": "User",
            "timezone": "Asia/Kolkata",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return {
        "email": unique_email,
        "password": "correct-horse-battery",
        "id": body["user"]["id"],
        "access_token": body["token"]["access_token"],
        "headers": {"Authorization": f"Bearer {body['token']['access_token']}"},
    }
