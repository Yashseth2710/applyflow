"""Data access for users and profiles."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Callers must pass an already-normalised (lowercase) address."""
        return self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        return (
            self.db.execute(select(User.id).where(User.email == email)).scalar_one_or_none()
            is not None
        )

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        timezone: str,
    ) -> User:
        """Creates the user and their profile together.

        A user without a profile would be an invalid state — every AI feature
        and every rendered timestamp depends on the profile existing.
        """
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )
        user.profile = Profile(timezone=timezone)

        self.db.add(user)
        self.db.flush()
        return user

    def update_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        self.db.flush()
