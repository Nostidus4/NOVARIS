"""Process-local authentication for development and UI evaluation only."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass
from uuid import uuid4

from qshield_api.domain.auth.entities import AuthRegistration, AuthSession, AuthUser
from qshield_api.domain.auth.provider import (
    InvalidCredentialsError,
    RegistrationError,
)

_PASSWORD_ITERATIONS = 240_000
_SESSION_LIFETIME_SECONDS = 12 * 60 * 60


@dataclass(frozen=True, slots=True)
class _StoredUser:
    user: AuthUser
    password_salt: bytes
    password_hash: bytes


@dataclass(frozen=True, slots=True)
class _StoredSession:
    email: str
    expires_at: int


class LocalAuthProvider:
    """Small in-memory provider enabled explicitly with QSHIELD_AUTH_PROVIDER=local."""

    def __init__(self) -> None:
        self._users: dict[str, _StoredUser] = {}
        self._sessions: dict[str, _StoredSession] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _password_hash(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            _PASSWORD_ITERATIONS,
        )

    def _create_session(self, user: AuthUser) -> AuthSession:
        access_token = secrets.token_urlsafe(40)
        refresh_token = secrets.token_urlsafe(40)
        expires_at = int(time.time()) + _SESSION_LIFETIME_SECONDS
        self._sessions[access_token] = _StoredSession(
            email=user.email,
            expires_at=expires_at,
        )
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=_SESSION_LIFETIME_SECONDS,
            expires_at=expires_at,
            user=user,
        )

    def login(self, email: str, password: str) -> AuthSession:
        normalized_email = email.strip().lower()
        with self._lock:
            stored = self._users.get(normalized_email)
            if stored is None:
                raise InvalidCredentialsError("Invalid authentication credentials.")
            candidate = self._password_hash(password, stored.password_salt)
            if not hmac.compare_digest(candidate, stored.password_hash):
                raise InvalidCredentialsError("Invalid authentication credentials.")
            return self._create_session(stored.user)

    def register(
        self, email: str, password: str, display_name: str
    ) -> AuthRegistration:
        normalized_email = email.strip().lower()
        with self._lock:
            if normalized_email in self._users:
                raise RegistrationError("Email is already registered.")
            salt = secrets.token_bytes(16)
            user = AuthUser(
                id=str(uuid4()),
                email=normalized_email,
                display_name=display_name,
            )
            self._users[normalized_email] = _StoredUser(
                user=user,
                password_salt=salt,
                password_hash=self._password_hash(password, salt),
            )
            session = self._create_session(user)
            return AuthRegistration(
                user=user,
                session=session,
                email_confirmation_required=False,
            )

    def get_user(self, access_token: str) -> AuthUser:
        with self._lock:
            session = self._sessions.get(access_token)
            if session is None or session.expires_at <= int(time.time()):
                self._sessions.pop(access_token, None)
                raise InvalidCredentialsError("Authentication session was not found.")
            stored = self._users.get(session.email)
            if stored is None:
                raise InvalidCredentialsError("Authentication user was not found.")
            return stored.user

    def logout(self, access_token: str) -> None:
        with self._lock:
            if self._sessions.pop(access_token, None) is None:
                raise InvalidCredentialsError("Authentication session was not found.")
