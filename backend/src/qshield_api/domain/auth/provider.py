"""Authentication provider port."""

from __future__ import annotations

from typing import Protocol

from qshield_api.domain.auth.entities import AuthRegistration, AuthSession, AuthUser


class InvalidCredentialsError(Exception):
    """Credentials or bearer session were rejected by the provider."""


class AuthProviderUnavailableError(Exception):
    """The configured authentication provider could not serve the request."""


class RegistrationError(Exception):
    """A registration request was rejected by the provider."""


class AuthProvider(Protocol):
    def login(self, email: str, password: str) -> AuthSession: ...

    def register(
        self, email: str, password: str, display_name: str
    ) -> AuthRegistration: ...

    def get_user(self, access_token: str) -> AuthUser: ...

    def logout(self, access_token: str) -> None: ...
