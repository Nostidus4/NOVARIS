"""Provider-neutral authentication entities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: str
    email: str
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class AuthSession:
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: int | None
    user: AuthUser


@dataclass(frozen=True, slots=True)
class AuthRegistration:
    user: AuthUser
    session: AuthSession | None
    email_confirmation_required: bool
