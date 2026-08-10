"""Account and profile endpoints."""

import base64
import io
import uuid

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.orm import Session

PASSWORD = "correct-horse-battery"


def _image(
    fmt: str = "PNG",
    size: tuple[int, int] = (600, 400),
    mode: str = "RGB",
    exif: bytes | None = None,
) -> bytes:
    image = Image.new(mode, size, (120, 90, 200))
    buffer = io.BytesIO()
    if exif is not None:
        image.save(buffer, format=fmt, exif=exif)
    else:
        image.save(buffer, format=fmt)
    return buffer.getvalue()


def _upload(client: TestClient, user: dict, data: bytes, content_type: str = "image/png"):
    return client.put(
        "/api/v1/users/me/avatar",
        headers=user["headers"],
        files={"file": ("me.png", io.BytesIO(data), content_type)},
    )


# ---- profile ----


def test_the_profile_can_be_read_back(client: TestClient, registered_user: dict) -> None:
    r = client.get("/api/v1/users/me", headers=registered_user["headers"])

    assert r.status_code == 200
    body = r.json()
    assert body["email"] == registered_user["email"]
    assert body["profile"]["timezone"] == "Asia/Kolkata"
    assert body["avatar"] is None


def test_the_fields_set_at_registration_are_finally_editable(
    client: TestClient, registered_user: dict
) -> None:
    """Every one of these existed in the database and had no endpoint to reach
    it, so they were write-once at sign-up."""
    r = client.patch(
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={
            "first_name": "Priya",
            "last_name": "Nair",
            "phone": "+91 98765 43210",
            "location": "Bengaluru",
            "linkedin_url": "https://linkedin.com/in/priya",
            "github_url": "https://github.com/priya",
            "portfolio_url": "https://priya.dev",
            "career_level": "mid",
            "years_experience": 4,
            "summary": "Backend engineer, mostly Python and Postgres.",
            "timezone": "Europe/London",
        },
    )

    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "Priya"
    assert body["profile"]["career_level"] == "mid"
    assert body["profile"]["years_experience"] == 4
    assert body["profile"]["timezone"] == "Europe/London"


def test_only_what_was_sent_changes(client: TestClient, registered_user: dict) -> None:
    """PATCH, not PUT. A form that saves one section must not blank the rest."""
    client.patch(
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"location": "Bengaluru", "summary": "Backend engineer."},
    )

    r = client.patch(
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"location": "Mumbai"},
    )

    assert r.json()["profile"]["summary"] == "Backend engineer."


def test_clearing_a_field_stores_nothing_rather_than_an_empty_string(
    client: TestClient, registered_user: dict
) -> None:
    """An emptied input arrives as "". Two representations of "no value" sort
    and compare differently, which is a bug waiting to happen."""
    client.patch(
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"location": "Bengaluru"},
    )

    r = client.patch(
        "/api/v1/users/me", headers=registered_user["headers"], json={"location": "   "}
    )

    assert r.json()["profile"]["location"] is None


def test_a_made_up_timezone_is_refused(client: TestClient, registered_user: dict) -> None:
    """A typo here silently shifts every timestamp on the site, and it would
    look like the data was wrong rather than the setting."""
    r = client.patch(
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"timezone": "Mars/Olympus_Mons"},
    )

    assert r.status_code == 422


def test_the_email_cannot_be_changed_here(client: TestClient, registered_user: dict) -> None:
    """Out of scope on purpose: it needs a verify-the-new-address flow, and
    accepting one without proof would lock people out of their own account.
    extra="forbid" makes that a refusal rather than a silent no-op."""
    r = client.patch(
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"email": "someone-else@example.com"},
    )

    assert r.status_code == 422
    assert (
        client.get("/api/v1/users/me", headers=registered_user["headers"]).json()["email"]
        == registered_user["email"]
    )


def test_a_blank_name_is_refused(client: TestClient, registered_user: dict) -> None:
    r = client.patch(
        "/api/v1/users/me", headers=registered_user["headers"], json={"first_name": "  "}
    )

    assert r.status_code == 422


def test_someone_elses_profile_is_unreachable(client: TestClient, registered_user: dict) -> None:
    """There is no id in the path at all — /me is the only way in, so an
    endpoint cannot forget the ownership check."""
    r = client.get("/api/v1/users/me")

    assert r.status_code == 401


# ---- avatar ----


def test_a_picture_can_be_set_and_comes_back_inline(
    client: TestClient, registered_user: dict
) -> None:
    """A data URI rather than a URL: the access token lives in memory and
    travels as a header, so a plain <img src> would get a 401."""
    r = _upload(client, registered_user, _image())

    assert r.status_code == 200
    assert r.json()["avatar"].startswith("data:image/webp;base64,")


def test_the_stored_picture_is_square_and_small(client: TestClient, registered_user: dict) -> None:
    body = _upload(client, registered_user, _image(size=(1200, 400))).json()
    raw = base64.b64decode(body["avatar"].split(",", 1)[1])

    with Image.open(io.BytesIO(raw)) as stored:
        assert stored.size == (256, 256)
        assert stored.format == "WEBP"


def test_location_data_does_not_survive_the_upload(
    client: TestClient, registered_user: dict
) -> None:
    """A phone photo carries EXIF, and EXIF carries where it was taken.
    Storing the original would publish someone's home address with their face.
    """
    exif = Image.Exif()
    exif[0x010F] = "TestPhone"  # Make
    exif[0x8825] = {1: "N", 2: (51.5, 30.0, 0.0), 3: "W", 4: (0.12, 0.0, 0.0)}  # GPSInfo

    original = _image(fmt="JPEG", exif=exif.tobytes())
    # The fixture is only worth anything if the tags really are in the file it
    # uploads — otherwise this passes by proving nothing.
    with Image.open(io.BytesIO(original)) as before:
        assert before.getexif()

    body = _upload(client, registered_user, original, "image/jpeg").json()
    raw = base64.b64decode(body["avatar"].split(",", 1)[1])

    with Image.open(io.BytesIO(raw)) as stored:
        assert not stored.getexif()


def test_a_file_that_is_not_an_image_is_refused(client: TestClient, registered_user: dict) -> None:
    """The content type is a string the client chose. Decoding is the check
    that actually means something."""
    r = _upload(client, registered_user, b"MZ\x90\x00 this is an executable", "image/png")

    assert r.status_code == 422


def test_a_format_we_do_not_want_is_refused(client: TestClient, registered_user: dict) -> None:
    """No SVG. It is a document that can carry script, and serving one back
    from our own origin is stored cross-site scripting, not a picture."""
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    r = _upload(client, registered_user, svg, "image/svg+xml")

    assert r.status_code == 422


def test_replacing_a_picture_does_not_leave_the_old_one_behind(
    client: TestClient, registered_user: dict, db_session: Session
) -> None:
    _upload(client, registered_user, _image())
    _upload(client, registered_user, _image(size=(300, 300)))

    stored = db_session.execute(
        text("SELECT count(*) FROM stored_files WHERE key LIKE :p"),
        {"p": f"avatars/{registered_user['id']}/%"},
    ).scalar_one()

    assert stored == 1


def test_the_picture_can_be_removed(client: TestClient, registered_user: dict) -> None:
    _upload(client, registered_user, _image())

    r = client.delete("/api/v1/users/me/avatar", headers=registered_user["headers"])

    assert r.status_code == 200
    assert r.json()["avatar"] is None


def test_signing_in_returns_the_picture(client: TestClient, registered_user: dict) -> None:
    """Otherwise the header shows initials until something else refreshes the
    session, which looks like the upload failed."""
    _upload(client, registered_user, _image())
    client.cookies.clear()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": PASSWORD},
    )

    assert r.json()["user"]["avatar"].startswith("data:image/webp;base64,")


# ---- password ----


def test_the_password_can_be_changed(client: TestClient, registered_user: dict) -> None:
    r = client.post(
        "/api/v1/users/me/password",
        headers=registered_user["headers"],
        json={"current_password": PASSWORD, "new_password": "a-brand-new-secret"},
    )
    assert r.status_code == 204

    client.cookies.clear()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": registered_user["email"], "password": "a-brand-new-secret"},
        ).status_code
        == 200
    )


def test_the_old_password_stops_working(client: TestClient, registered_user: dict) -> None:
    client.post(
        "/api/v1/users/me/password",
        headers=registered_user["headers"],
        json={"current_password": PASSWORD, "new_password": "a-brand-new-secret"},
    )
    client.cookies.clear()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": PASSWORD},
    )

    assert r.status_code == 401


def test_changing_the_password_needs_the_current_one(
    client: TestClient, registered_user: dict
) -> None:
    """A signed-in session is not enough on its own — an unattended laptop
    would otherwise be a way to take the account permanently."""
    r = client.post(
        "/api/v1/users/me/password",
        headers=registered_user["headers"],
        json={"current_password": "not-it", "new_password": "a-brand-new-secret"},
    )

    assert r.status_code == 403


def test_a_short_new_password_is_refused(client: TestClient, registered_user: dict) -> None:
    r = client.post(
        "/api/v1/users/me/password",
        headers=registered_user["headers"],
        json={"current_password": PASSWORD, "new_password": "short"},
    )

    assert r.status_code == 422


# ---- deletion ----


def test_the_account_and_everything_in_it_goes(
    client: TestClient, registered_user: dict, db_session: Session
) -> None:
    client.post(
        "/api/v1/applications",
        headers=registered_user["headers"],
        json={"company_name": "Acme", "job_title": "Engineer"},
    )
    _upload(client, registered_user, _image())

    r = client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"password": PASSWORD},
    )

    assert r.status_code == 204
    user_id = uuid.UUID(registered_user["id"])
    for table, column in (
        ("users", "id"),
        ("profiles", "user_id"),
        ("applications", "user_id"),
        ("stored_files", "owner_id"),
    ):
        left = db_session.execute(
            text(f"SELECT count(*) FROM {table} WHERE {column} = :id"), {"id": user_id}
        ).scalar_one()
        assert left == 0, f"{table} still holds rows for a deleted account"


def test_deleting_needs_the_password(client: TestClient, registered_user: dict) -> None:
    """Irreversible and total, so a session alone is not enough."""
    r = client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"password": "not-it"},
    )

    assert r.status_code == 403
    assert client.get("/api/v1/users/me", headers=registered_user["headers"]).status_code == 200


def test_a_deleted_account_cannot_sign_in(client: TestClient, registered_user: dict) -> None:
    client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"password": PASSWORD},
    )
    client.cookies.clear()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": PASSWORD},
    )

    assert r.status_code == 401


def test_deleting_frees_the_email_for_a_new_account(
    client: TestClient, registered_user: dict
) -> None:
    """The row is gone rather than flagged, so the address is genuinely free —
    a soft delete would leave someone unable to sign up again."""
    email = registered_user["email"]
    client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=registered_user["headers"],
        json={"password": PASSWORD},
    )
    client.cookies.clear()

    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert r.status_code == 201
