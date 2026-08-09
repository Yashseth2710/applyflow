"""The storage contract.

Both backends are held to the same expectations, so swapping one for the other
can't quietly change behaviour the rest of the app depends on.
"""

import uuid
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.storage import (
    FileNotStored,
    LocalStorage,
    PostgresStorage,
    Storage,
    StorageError,
    build_key,
)
from app.models.stored_file import StoredFile

CONTENT = b"%PDF-1.4 pretend this is a resume"


@pytest.fixture(params=["postgres", "local"])
def storage(request, db_session: Session, tmp_path: Path) -> Storage:
    if request.param == "postgres":
        return PostgresStorage(db_session)
    return LocalStorage(tmp_path)


def test_saved_content_comes_back_unchanged(storage: Storage):
    storage.save("resumes/a/b.pdf", BytesIO(CONTENT))
    assert storage.open("resumes/a/b.pdf").read() == CONTENT


def test_exists_tracks_saves_and_deletes(storage: Storage):
    key = "resumes/a/b.pdf"
    assert storage.exists(key) is False

    storage.save(key, BytesIO(CONTENT))
    assert storage.exists(key) is True

    storage.delete(key)
    assert storage.exists(key) is False


def test_opening_a_missing_key_raises(storage: Storage):
    with pytest.raises(FileNotStored):
        storage.open("resumes/nope/missing.pdf")


def test_deleting_a_missing_key_is_not_an_error(storage: Storage):
    """The desired end state is "not there", which it already is."""
    storage.delete("resumes/nope/missing.pdf")


def test_saving_the_same_key_replaces_the_content(storage: Storage):
    key = "resumes/a/b.pdf"
    storage.save(key, BytesIO(CONTENT))
    storage.save(key, BytesIO(b"%PDF-1.4 a newer file"))

    assert storage.open(key).read() == b"%PDF-1.4 a newer file"


def test_empty_content_round_trips(storage: Storage):
    storage.save("resumes/a/empty.pdf", BytesIO(b""))
    assert storage.open("resumes/a/empty.pdf").read() == b""


# ---- backend specifics ----


def test_local_storage_refuses_to_escape_its_root(tmp_path: Path):
    """Keys are ours today, but one day one will come from a request."""
    storage = LocalStorage(tmp_path / "root")
    with pytest.raises(StorageError):
        storage.save("../escaped.pdf", BytesIO(CONTENT))


def test_postgres_storage_records_the_owner(db_session: Session, registered_user: dict):
    """Ownership is what lets the database clean the bytes up with the account."""
    owner = uuid.UUID(registered_user["id"])
    storage = PostgresStorage(db_session)
    storage.save("resumes/x/y.pdf", BytesIO(CONTENT), owner_id=owner)

    row = db_session.execute(
        select(StoredFile).where(StoredFile.key == "resumes/x/y.pdf")
    ).scalar_one()
    assert row.owner_id == owner
    assert row.size_bytes == len(CONTENT)


def test_postgres_storage_rolls_back_with_its_session(db_session: Session):
    """The whole reason for sharing the session: no orphaned bytes."""
    storage = PostgresStorage(db_session)
    storage.save("resumes/x/rollback.pdf", BytesIO(CONTENT))
    assert storage.exists("resumes/x/rollback.pdf") is True

    db_session.rollback()
    assert storage.exists("resumes/x/rollback.pdf") is False


# ---- key building ----


@pytest.mark.parametrize(
    ("filename", "expected_suffix"),
    [
        ("resume.pdf", ".pdf"),
        ("RESUME.PDF", ".pdf"),
        ("resume", ".bin"),
        ("../../etc/passwd", ".bin"),
    ],
)
def test_keys_ignore_the_supplied_filename(filename: str, expected_suffix: str):
    """Only the extension survives — the rest is user input, and the real name
    is kept in the database anyway."""
    user_id, resume_id = uuid.uuid4(), uuid.uuid4()
    key = build_key(user_id, resume_id, filename)

    assert key == f"resumes/{user_id}/{resume_id}{expected_suffix}"
    assert ".." not in key


def test_keys_are_scoped_per_user():
    resume_id = uuid.uuid4()
    a, b = uuid.uuid4(), uuid.uuid4()
    assert build_key(a, resume_id, "r.pdf") != build_key(b, resume_id, "r.pdf")


# Guards against a future backend quietly dropping a method.
def test_every_backend_implements_the_interface(storage: Storage):
    for name in ("save", "open", "delete", "exists"):
        method: Callable[..., object] = getattr(storage, name)
        assert callable(method)
