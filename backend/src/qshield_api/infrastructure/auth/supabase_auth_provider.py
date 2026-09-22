"""Supabase Auth adapter for Q-SHIELD authentication."""

from __future__ import annotations

from typing import Any

from supabase_auth.errors import (
    AuthApiError,
    AuthInvalidCredentialsError,
    AuthInvalidJwtError,
    AuthRetryableError,
    AuthSessionMissingError,
)

from qshield_api.domain.auth.entities import AuthRegistration, AuthSession, AuthUser
from qshield_api.domain.auth.provider import (
    AuthProviderUnavailableError,
    InvalidCredentialsError,
    RegistrationError,
)
from qshield_api.infrastructure.persistence.supabase_client import SupabaseSettings
from supabase import create_client

_INVALID_AUTH_ERRORS = (
    AuthInvalidCredentialsError,
    AuthInvalidJwtError,
    AuthSessionMissingError,
)


class SupabaseAuthProvider:
    """Authenticate users without sharing mutable auth state between requests."""

    def __init__(
        self, settings: SupabaseSettings, *, auto_confirm_registration: bool = False
    ) -> None:
        self._settings = settings
        self._auto_confirm_registration = auto_confirm_registration

    @staticmethod
    def _display_name(user: Any) -> str | None:
        metadata = user.user_metadata or {}
        value = metadata.get("full_name") or metadata.get("name")
        return str(value) if value else None

    @classmethod
    def _to_user(cls, user: Any) -> AuthUser:
        if user is None or not user.id or not user.email:
            raise InvalidCredentialsError(
                "Provider response did not contain a valid user."
            )
        return AuthUser(
            id=str(user.id),
            email=str(user.email),
            display_name=cls._display_name(user),
        )

    @staticmethod
    def _map_error(exc: Exception) -> Exception:
        if isinstance(exc, _INVALID_AUTH_ERRORS):
            return InvalidCredentialsError("Invalid authentication credentials.")
        if isinstance(exc, AuthApiError) and exc.status in {400, 401, 403}:
            return InvalidCredentialsError("Invalid authentication credentials.")
        if isinstance(exc, (AuthRetryableError, AuthApiError)):
            return AuthProviderUnavailableError("Supabase Auth is unavailable.")
        return AuthProviderUnavailableError("Authentication provider request failed.")

    def login(self, email: str, password: str) -> AuthSession:
        try:
            client = create_client(self._settings.url, self._settings.publishable_key)
            response = client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            raise self._map_error(exc) from exc

        session = response.session
        if session is None:
            raise InvalidCredentialsError("Authentication did not return a session.")
        return AuthSession(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            expires_at=session.expires_at,
            user=self._to_user(session.user),
        )

    def register(
        self, email: str, password: str, display_name: str
    ) -> AuthRegistration:
        try:
            if self._auto_confirm_registration:
                admin_client = create_client(
                    self._settings.url,
                    self._settings.secret_key,
                )
                admin_client.auth.admin.create_user(
                    {
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {"full_name": display_name},
                    }
                )
                session = self.login(email, password)
                return AuthRegistration(
                    user=session.user,
                    session=session,
                    email_confirmation_required=False,
                )

            client = create_client(self._settings.url, self._settings.publishable_key)
            response = client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": display_name}},
                }
            )
        except RegistrationError:
            raise
        except AuthApiError as exc:
            if exc.status in {400, 409, 422}:
                raise RegistrationError("Registration request was rejected.") from exc
            raise AuthProviderUnavailableError("Supabase Auth is unavailable.") from exc
        except Exception as exc:
            raise AuthProviderUnavailableError(
                "Authentication provider request failed."
            ) from exc

        user = self._to_user(response.user)
        session = response.session
        auth_session = None
        if session is not None:
            auth_session = AuthSession(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                expires_in=session.expires_in,
                expires_at=session.expires_at,
                user=self._to_user(session.user),
            )
        return AuthRegistration(
            user=user,
            session=auth_session,
            email_confirmation_required=session is None,
        )

    def get_user(self, access_token: str) -> AuthUser:
        try:
            client = create_client(self._settings.url, self._settings.publishable_key)
            response = client.auth.get_user(access_token)
        except Exception as exc:
            raise self._map_error(exc) from exc
        if response is None:
            raise InvalidCredentialsError("Authentication session was not found.")
        return self._to_user(response.user)

    def logout(self, access_token: str) -> None:
        try:
            admin_client = create_client(self._settings.url, self._settings.secret_key)
            admin_client.auth.admin.sign_out(access_token, scope="global")
        except Exception as exc:
            raise self._map_error(exc) from exc
