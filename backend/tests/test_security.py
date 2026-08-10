"""Password hashing and tokens, below the HTTP layer."""

from app.core.security import hash_password, needs_rehash, verify_password

#: A real Argon2id hash of PASSWORD, written down rather than generated.
#:
#: Generating it in the test would prove nothing: it would use whatever
#: parameters the installed library currently defaults to, so both sides would
#: move together and the test would pass through any change at all. Frozen, it
#: stands in for the hashes already sitting in the database — including the
#: ones written before the last argon2-cffi upgrade.
STORED_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "LxGqwDleV+GU2m6MU3/FPw$ahpoG0QLWUy2ZGUJUlgMGGvj/KtdCj1PTSFDRp4d2XY"
)
PASSWORD = "correct-horse-battery"


def test_a_hash_written_by_an_older_version_still_verifies() -> None:
    """The failure this guards against locks every existing account out at
    once, and does it quietly: nothing errors, sign-in simply stops working
    for everyone who has not changed their password since the upgrade."""
    assert verify_password(PASSWORD, STORED_HASH) is True


def test_the_wrong_password_is_still_wrong() -> None:
    assert verify_password("not the password", STORED_HASH) is False


def test_a_stored_hash_is_not_needlessly_rehashed() -> None:
    """If this starts failing, the library's default parameters have moved.
    That is not a bug — sign-in upgrades the hash in place — but it is worth
    knowing about deliberately rather than discovering in a profiler."""
    assert needs_rehash(STORED_HASH) is False


def test_rubbish_is_rejected_rather_than_raised() -> None:
    """Callers treat the return value as the answer. An exception here would
    surface as a 500 on a login attempt with a corrupted row."""
    assert verify_password(PASSWORD, "not a hash at all") is False


def test_the_same_password_hashes_differently_every_time() -> None:
    """Salted. Two accounts with the same password must not be visibly the
    same in the database."""
    assert hash_password(PASSWORD) != hash_password(PASSWORD)
