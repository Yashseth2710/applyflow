"""Authentication business logic.

Knows nothing about HTTP — it raises domain errors and the API layer maps them
to status codes.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class AccountDisabled(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


# Argon2 verification of a throwaway hash, used to keep the timing of a
# "no such user" login indistinguishable from a wrong-password login.
# Without it, response time reveals which emails are registered.
_DUMMY_HASH = hash_password("timing-attack-mitigation-placeholder")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        timezone: str | None,
    ) -> User:
        if self.users.email_exists(email):
            raise EmailAlreadyRegistered

        user = self.users.create(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            timezone=timezone or settings.DEFAULT_TIMEZONE,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.users.get_by_email(email)

        if user is None:
            # Do the work anyway so both branches cost the same.
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentials

        if not verify_password(password, user.password_hash):
            raise InvalidCredentials

        if not user.is_active:
            raise AccountDisabled

        # Transparently upgrade hashes if the Argon2 parameters have changed
        # since this password was set.
        if needs_rehash(user.password_hash):
            self.users.update_password_hash(user, hash_password(password))
            self.db.commit()

        return user

    def user_from_refresh_token(self, token: str) -> User:
        try:
            subject = decode_token(token, expected_type="refresh")
            user_id = uuid.UUID(subject)
        except (TokenError, ValueError) as exc:
            raise InvalidRefreshToken from exc

        user = self.users.get_by_id(user_id)
        if user is None:
            raise InvalidRefreshToken
        if not user.is_active:
            raise AccountDisabled

        return user

    @staticmethod
    def issue_tokens(user: User) -> tuple[str, str]:
        """Returns (access_token, refresh_token)."""
        subject = str(user.id)
        return create_access_token(subject), create_refresh_token(subject)
