"""Account and profile changes.

Knows nothing about HTTP — it raises domain errors and the API layer maps them.
"""

import base64
import io
import logging
from typing import IO

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.core.storage import FileNotStored, Storage, StorageError, build_storage
from app.models.profile import Profile
from app.models.user import User
from app.schemas.user import ProfileUpdate
from app.services.avatar import CONTENT_TYPE, InvalidAvatar, normalise, storage_key

logger = logging.getLogger(__name__)


class IncorrectPassword(Exception):
    """The current password given does not match."""


class SamePassword(Exception):
    """The new password is the one already set."""


class UserService:
    def __init__(self, db: Session, storage: Storage | None = None) -> None:
        self.db = db
        self.storage = storage or build_storage(db)

    # ---- profile ----

    def update(self, user: User, payload: ProfileUpdate) -> User:
        """Name lives on the user, everything else on the profile.

        One endpoint for both because that is one form on screen, and splitting
        it would mean a page that can half-save.
        """
        data = payload.model_dump(exclude_unset=True)

        for field in ("first_name", "last_name"):
            if field in data:
                setattr(user, field, data.pop(field))

        profile = self._profile(user)
        for field, value in data.items():
            setattr(profile, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def _profile(self, user: User) -> Profile:
        """Every account gets one at registration, but a row can go missing —
        a restore, a hand-written insert — and losing the settings page over it
        would be a poor trade."""
        if user.profile is None:
            profile = Profile(user_id=user.id)
            self.db.add(profile)
            self.db.flush()
            user.profile = profile
        return user.profile

    # ---- avatar ----

    def set_avatar(self, user: User, source: IO[bytes], content_type: str | None) -> User:
        """Replace the picture. Raises InvalidAvatar if it is not usable."""
        encoded = normalise(source, content_type)

        profile = self._profile(user)
        previous = profile.avatar_key
        key = storage_key(user.id)

        self.storage.save(key, io.BytesIO(encoded), owner_id=user.id)
        profile.avatar_key = key

        # Delete the old one before committing, not after. A delete issued
        # afterwards opens a second transaction that nothing ever commits,
        # leaving the bytes behind once the row pointing at them is gone.
        if previous:
            self._forget(previous)

        self.db.commit()
        self.db.refresh(user)
        return user

    def clear_avatar(self, user: User) -> User:
        profile = self._profile(user)
        if profile.avatar_key:
            self._forget(profile.avatar_key)
            profile.avatar_key = None
            self.db.commit()
            self.db.refresh(user)
        return user

    def _forget(self, key: str) -> None:
        try:
            self.storage.delete(key)
        except StorageError:
            # The row is what decides whether an avatar exists. Orphaned bytes
            # are waste; a failed request over them would be a bug the user
            # cannot do anything about.
            logger.warning("Could not delete avatar %s", key, exc_info=True)

    def avatar_data_uri(self, user: User) -> str | None:
        """The picture inlined into the JSON, or None.

        A URL would be the obvious choice and does not work here: the access
        token lives in memory and is sent as a header, so a plain `<img src>`
        arrives unauthenticated and gets a 401. Inlining costs a few kilobytes
        on a response the client already makes on every page load.
        """
        profile = user.profile
        if profile is None or not profile.avatar_key:
            return None

        try:
            with self.storage.open(profile.avatar_key) as handle:
                data = handle.read()
        except FileNotStored:
            # The bytes went missing under the row. Show initials rather than
            # failing the whole session-restore request over a picture.
            logger.warning("Avatar %s is missing its file", profile.avatar_key)
            return None
        except StorageError:
            logger.warning("Could not read avatar %s", profile.avatar_key, exc_info=True)
            return None

        return f"data:{CONTENT_TYPE};base64,{base64.b64encode(data).decode()}"

    # ---- credentials ----

    def change_password(self, user: User, *, current: str, new: str) -> None:
        """Requires the current password.

        A signed-in session is not enough on its own: an unattended laptop, or a
        stolen token, would otherwise be a way to take the account permanently
        rather than until the token expired.
        """
        if not verify_password(current, user.password_hash):
            raise IncorrectPassword
        if verify_password(new, user.password_hash):
            raise SamePassword

        user.password_hash = hash_password(new)
        self.db.commit()

    def delete_account(self, user: User, *, password: str) -> None:
        """Irreversible, so it asks for the password too.

        Every table cascades from `users`, including `stored_files`, so one
        delete takes the applications, resumes, interviews, generated answers
        and uploaded bytes with it. Nothing is kept for later.
        """
        if not verify_password(password, user.password_hash):
            raise IncorrectPassword

        user_id = user.id
        self.db.delete(user)
        self.db.commit()
        logger.info("Deleted account %s", user_id)


# Re-exported so the API layer imports every error it has to map from one
# place, rather than reaching into the avatar module for one of them.
__all__ = ["IncorrectPassword", "InvalidAvatar", "SamePassword", "UserService"]
