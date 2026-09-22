"""Authentication use cases; provider details stay in infrastructure."""

from qshield_api.application.auth.dto import (
    AuthUserDTO,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    SessionResponse,
)
from qshield_api.domain.auth.entities import AuthUser
from qshield_api.domain.auth.provider import AuthProvider


def _user_dto(user: AuthUser) -> AuthUserDTO:
    return AuthUserDTO(id=user.id, email=user.email, display_name=user.display_name)


def login(credentials: LoginRequest, provider: AuthProvider) -> LoginResponse:
    session = provider.login(
        email=str(credentials.email),
        password=credentials.password.get_secret_value(),
    )
    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        expires_at=session.expires_at,
        user=_user_dto(session.user),
    )


def register(credentials: RegisterRequest, provider: AuthProvider) -> RegisterResponse:
    result = provider.register(
        email=str(credentials.email),
        password=credentials.password.get_secret_value(),
        display_name=credentials.display_name,
    )
    session = result.session
    return RegisterResponse(
        user=_user_dto(result.user),
        email_confirmation_required=result.email_confirmation_required,
        access_token=session.access_token if session else None,
        refresh_token=session.refresh_token if session else None,
        expires_in=session.expires_in if session else None,
        expires_at=session.expires_at if session else None,
    )


def get_current_session(access_token: str, provider: AuthProvider) -> SessionResponse:
    return SessionResponse(user=_user_dto(provider.get_user(access_token)))


def logout(access_token: str, provider: AuthProvider) -> LogoutResponse:
    provider.logout(access_token)
    return LogoutResponse()
