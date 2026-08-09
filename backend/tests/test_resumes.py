"""Resume upload, versioning, extraction and access control."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.api.deps import get_storage
from app.core.storage import PostgresStorage
from app.main import app
from app.models.stored_file import StoredFile

RESUME_LINES = [
    "Yash Seth",
    "Backend Engineer",
    "Bengaluru, India",
    "",
    "Experience",
    "Built and shipped a job application tracker.",
    "Worked with Python, FastAPI and PostgreSQL.",
    "Designed the schema and the migration path.",
    "",
    "Education",
    "Bachelor of Engineering, Computer Science.",
    "Graduated with distinction.",
]


def build_pdf(lines: list[str] | None = None) -> bytes:
    """A minimal but genuinely valid PDF.

    Written by hand rather than pulled from a fixture file so the tests exercise
    real parsing, and so passing no lines gives us a text-free PDF — the same
    thing pypdf sees when someone uploads a scan.
    """
    content = "BT\n/F1 12 Tf\n72 720 Td\n14 TL\n"
    for line in lines or []:
        content += f"({line}) Tj\nT*\n"
    content += "ET"
    stream = content.encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


@pytest.fixture
def resume_client(client: TestClient, db_session: Session) -> Generator[TestClient, None, None]:
    """Client wired to the same storage backend production uses.

    Bound to the test's session, so uploaded bytes roll back with everything
    else rather than accumulating in the database.
    """
    app.dependency_overrides[get_storage] = lambda: PostgresStorage(db_session)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_storage, None)


def stored_keys(db: Session) -> list[str]:
    return list(db.execute(select(StoredFile.key)).scalars().all())


def upload(
    client: TestClient,
    user: dict,
    *,
    content: bytes | None = None,
    filename: str = "my-resume.pdf",
    content_type: str = "application/pdf",
    **data: object,
):
    return client.post(
        "/api/v1/resumes",
        headers=user["headers"],
        files={
            "file": (
                filename,
                content if content is not None else build_pdf(RESUME_LINES),
                content_type,
            )
        },
        data=data,
    )


# ---- upload ----


def test_upload_stores_file_and_extracts_text(resume_client, registered_user, db_session):
    r = upload(resume_client, registered_user, title="Backend resume")
    assert r.status_code == 201, r.text

    body = r.json()
    assert body["title"] == "Backend resume"
    assert body["version"] == 1
    assert body["is_current"] is True
    assert body["original_filename"] == "my-resume.pdf"
    assert body["extraction_status"] == "ok"
    assert body["size_bytes"] > 0

    # The bytes actually reached storage.
    stored = db_session.execute(select(StoredFile)).scalars().all()
    assert len(stored) == 1
    assert stored[0].content.startswith(b"%PDF-")
    assert stored[0].owner_id is not None

    text = resume_client.get(
        f"/api/v1/resumes/{body['id']}/text", headers=registered_user["headers"]
    ).json()
    assert "Backend Engineer" in text["extracted_text"]
    assert "FastAPI" in text["extracted_text"]


def test_title_falls_back_to_the_filename(resume_client, registered_user):
    r = upload(resume_client, registered_user, filename="senior_backend_cv.pdf")
    assert r.json()["title"] == "senior backend cv"


def test_scanned_pdf_is_kept_but_flagged(resume_client, registered_user):
    """No extractable text is not a failed upload — the file is still stored."""
    r = upload(resume_client, registered_user, content=build_pdf([]))
    assert r.status_code == 201

    body = r.json()
    assert body["extraction_status"] == "empty"
    assert "scanned" in body["extraction_error"].lower()


def test_non_pdf_is_rejected(resume_client, registered_user):
    r = upload(
        resume_client,
        registered_user,
        content=b"just some text",
        filename="resume.txt",
        content_type="text/plain",
    )
    assert r.status_code == 422
    assert "PDF" in r.json()["detail"]


def test_file_pretending_to_be_a_pdf_is_rejected(resume_client, registered_user):
    """Extension and content type are both client-supplied; the bytes are not."""
    r = upload(resume_client, registered_user, content=b"MZ\x90\x00 not a pdf at all")
    assert r.status_code == 422
    assert "contents are not" in r.json()["detail"]


def test_empty_file_is_rejected(resume_client, registered_user):
    r = upload(resume_client, registered_user, content=b"")
    assert r.status_code == 422
    assert "empty" in r.json()["detail"].lower()


def test_oversized_file_is_rejected(resume_client, registered_user):
    from app.core.config import settings

    oversized = b"%PDF-" + b"0" * (settings.max_upload_bytes + 1)
    r = upload(resume_client, registered_user, content=oversized)
    assert r.status_code == 422
    assert "larger than" in r.json()["detail"]


def test_identical_upload_is_flagged_but_allowed(resume_client, registered_user):
    first = upload(resume_client, registered_user, title="One").json()
    second = upload(resume_client, registered_user, title="Two")

    assert second.status_code == 201
    body = second.json()
    assert body["duplicate_of_id"] == first["id"]
    assert body["duplicate_of_title"] == "One"
    # Still a separate resume, not a silent merge.
    assert body["id"] != first["id"]


# ---- versioning ----


def test_new_version_supersedes_the_previous_one(resume_client, registered_user):
    first = upload(resume_client, registered_user, title="Backend resume").json()

    second = upload(
        resume_client,
        registered_user,
        content=build_pdf([*RESUME_LINES, "Now with a rewritten summary."]),
        replaces_id=first["id"],
    )
    assert second.status_code == 201

    body = second.json()
    assert body["version"] == 2
    assert body["is_current"] is True
    assert body["family_id"] == first["family_id"]
    # Title carries over rather than reverting to the filename.
    assert body["title"] == "Backend resume"

    versions = resume_client.get(
        f"/api/v1/resumes/{first['id']}/versions", headers=registered_user["headers"]
    ).json()
    assert [v["version"] for v in versions] == [2, 1]
    assert [v["is_current"] for v in versions] == [True, False]


def test_list_shows_one_row_per_resume(resume_client, registered_user):
    first = upload(resume_client, registered_user, title="Backend").json()
    upload(resume_client, registered_user, replaces_id=first["id"])
    upload(resume_client, registered_user, content=build_pdf(["Different file"]), title="Data")

    listed = resume_client.get("/api/v1/resumes", headers=registered_user["headers"]).json()
    assert len(listed) == 2
    assert {r["title"] for r in listed} == {"Backend", "Data"}
    assert all(r["is_current"] for r in listed)


def test_an_older_version_can_be_made_current_again(resume_client, registered_user):
    first = upload(resume_client, registered_user, title="Backend").json()
    second = upload(resume_client, registered_user, replaces_id=first["id"]).json()

    r = resume_client.post(
        f"/api/v1/resumes/{first['id']}/set-current", headers=registered_user["headers"]
    )
    assert r.status_code == 200
    assert r.json()["is_current"] is True

    versions = resume_client.get(
        f"/api/v1/resumes/{second['id']}/versions", headers=registered_user["headers"]
    ).json()
    current = [v for v in versions if v["is_current"]]
    assert len(current) == 1
    assert current[0]["id"] == first["id"]


def test_versioning_an_unknown_resume_is_a_404(resume_client, registered_user):
    r = upload(
        resume_client,
        registered_user,
        replaces_id="00000000-0000-0000-0000-000000000000",
    )
    assert r.status_code == 404


# ---- download ----


def test_download_returns_the_original_bytes(resume_client, registered_user):
    content = build_pdf(RESUME_LINES)
    uploaded = upload(resume_client, registered_user, content=content).json()

    r = resume_client.get(
        f"/api/v1/resumes/{uploaded['id']}/download", headers=registered_user["headers"]
    )
    assert r.status_code == 200
    assert r.content == content
    assert r.headers["content-type"] == "application/pdf"
    assert "my-resume.pdf" in r.headers["content-disposition"]


def test_download_reports_a_missing_file_rather_than_crashing(
    resume_client, registered_user, db_session
):
    """Shouldn't happen now that the bytes commit with the row, but a resume
    restored from an older backup could still land here."""
    uploaded = upload(resume_client, registered_user).json()
    db_session.query(StoredFile).delete()
    db_session.flush()

    r = resume_client.get(
        f"/api/v1/resumes/{uploaded['id']}/download", headers=registered_user["headers"]
    )
    assert r.status_code == 503
    assert "upload it again" in r.json()["detail"]


# ---- metadata ----


def test_details_can_be_edited(resume_client, registered_user):
    uploaded = upload(resume_client, registered_user).json()

    r = resume_client.patch(
        f"/api/v1/resumes/{uploaded['id']}",
        headers=registered_user["headers"],
        json={"title": "Renamed", "notes": "  sent to product roles  "},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"
    assert r.json()["notes"] == "sent to product roles"


def test_detail_includes_the_version_history(resume_client, registered_user):
    first = upload(resume_client, registered_user, title="Backend").json()
    upload(resume_client, registered_user, replaces_id=first["id"])

    body = resume_client.get(
        f"/api/v1/resumes/{first['id']}", headers=registered_user["headers"]
    ).json()
    assert len(body["versions"]) == 2
    assert body["extracted_text"] is not None


def test_limits_are_published(resume_client, registered_user):
    r = resume_client.get("/api/v1/resumes/limits")
    assert r.status_code == 200
    assert r.json()["allowed_types"] == ["application/pdf"]
    assert r.json()["max_size_bytes"] > 0


# ---- link to applications ----


def _create_application(client: TestClient, user: dict, **extra: object) -> dict:
    r = client.post(
        "/api/v1/applications",
        headers=user["headers"],
        json={"company_name": "Acme", "job_title": "Backend Engineer", **extra},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_application_can_reference_a_resume(resume_client, registered_user):
    uploaded = upload(resume_client, registered_user).json()
    application = _create_application(resume_client, registered_user, resume_id=uploaded["id"])
    assert application["resume_id"] == uploaded["id"]

    usage = resume_client.get(
        f"/api/v1/resumes/{uploaded['id']}/usage", headers=registered_user["headers"]
    ).json()
    assert usage["application_count"] == 1


def test_deleting_a_resume_keeps_the_application(resume_client, registered_user):
    """The record of having applied matters more than the file."""
    uploaded = upload(resume_client, registered_user).json()
    application = _create_application(resume_client, registered_user, resume_id=uploaded["id"])

    r = resume_client.delete(
        f"/api/v1/resumes/{uploaded['id']}", headers=registered_user["headers"]
    )
    assert r.status_code == 204

    after = resume_client.get(
        f"/api/v1/applications/{application['id']}", headers=registered_user["headers"]
    ).json()
    assert after["resume_id"] is None
    assert after["company_name"] == "Acme"


def test_deleting_the_current_version_promotes_the_previous_one(resume_client, registered_user):
    first = upload(resume_client, registered_user, title="Backend").json()
    second = upload(resume_client, registered_user, replaces_id=first["id"]).json()

    resume_client.delete(f"/api/v1/resumes/{second['id']}", headers=registered_user["headers"])

    listed = resume_client.get("/api/v1/resumes", headers=registered_user["headers"]).json()
    assert [r["id"] for r in listed] == [first["id"]]


def test_deleting_removes_the_stored_file(resume_client, registered_user, db_session):
    uploaded = upload(resume_client, registered_user).json()
    assert stored_keys(db_session)

    resume_client.delete(f"/api/v1/resumes/{uploaded['id']}", headers=registered_user["headers"])
    assert stored_keys(db_session) == []


def test_deleting_the_account_removes_its_files(resume_client, registered_user, db_session):
    """The bytes hang off the user, so the database cleans them up rather than
    trusting the application to remember."""
    upload(resume_client, registered_user)
    assert stored_keys(db_session)

    db_session.execute(sql_text("DELETE FROM users WHERE id = :id"), {"id": registered_user["id"]})
    db_session.flush()

    assert stored_keys(db_session) == []


# ---- access control ----


def test_resumes_require_authentication(resume_client):
    assert resume_client.get("/api/v1/resumes").status_code == 401


@pytest.mark.parametrize(
    ("method", "suffix"),
    [
        ("get", ""),
        ("get", "/text"),
        ("get", "/versions"),
        ("get", "/download"),
        ("get", "/usage"),
        ("delete", ""),
    ],
)
def test_another_users_resume_is_not_reachable(
    resume_client, registered_user, other_user, method, suffix
):
    uploaded = upload(resume_client, registered_user).json()

    r = getattr(resume_client, method)(
        f"/api/v1/resumes/{uploaded['id']}{suffix}", headers=other_user["headers"]
    )
    # 404 rather than 403 — a 403 would confirm the id exists.
    assert r.status_code == 404


def test_another_user_cannot_edit_a_resume(resume_client, registered_user, other_user):
    uploaded = upload(resume_client, registered_user).json()

    r = resume_client.patch(
        f"/api/v1/resumes/{uploaded['id']}",
        headers=other_user["headers"],
        json={"title": "Mine now"},
    )
    assert r.status_code == 404


def test_another_users_resume_does_not_appear_in_the_list(
    resume_client, registered_user, other_user
):
    upload(resume_client, registered_user)
    assert resume_client.get("/api/v1/resumes", headers=other_user["headers"]).json() == []
