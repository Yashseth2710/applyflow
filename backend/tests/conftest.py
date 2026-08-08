"""Shared test fixtures."""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.main import app


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
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    """Unique per test, so a leaked row can never collide with a later run."""
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


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
