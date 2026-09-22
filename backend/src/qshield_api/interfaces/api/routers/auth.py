"""Authentication HTTP endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from qshield_api.application.auth.dto import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    SessionResponse,
)
from qshield_api.application.auth.use_cases import (
    get_current_session,
    login,
    logout,
    register,
)
from qshield_api.deps import get_auth_provider
from qshield_api.domain.auth.provider import (
    AuthProvider,
    AuthProviderUnavailableError,
    InvalidCredentialsError,
    RegistrationError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


def _raise_auth_http_error(exc: Exception) -> None:
    if isinstance(exc, InvalidCredentialsError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Dịch vụ đăng nhập đang tạm thời gián đoạn. Vui lòng thử lại sau.",
    ) from exc


@router.post("/login", response_model=LoginResponse)
def login_endpoint(
    credentials: LoginRequest,
    provider: AuthProvider = Depends(get_auth_provider),
) -> LoginResponse:
    try:
        return login(credentials, provider)
    except (InvalidCredentialsError, AuthProviderUnavailableError) as exc:
        _raise_auth_http_error(exc)


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
def register_endpoint(
    credentials: RegisterRequest,
    provider: AuthProvider = Depends(get_auth_provider),
) -> RegisterResponse:
    try:
        return register(credentials, provider)
    except RegistrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Không thể tạo tài khoản. Email có thể đã được sử dụng hoặc mật khẩu "
                "chưa đáp ứng yêu cầu bảo mật."
            ),
        ) from exc
    except AuthProviderUnavailableError as exc:
        _raise_auth_http_error(exc)


@router.get("/me", response_model=SessionResponse)
def me_endpoint(
    token: str = Depends(bearer_token),
    provider: AuthProvider = Depends(get_auth_provider),
) -> SessionResponse:
    try:
        return get_current_session(token, provider)
    except (InvalidCredentialsError, AuthProviderUnavailableError) as exc:
        _raise_auth_http_error(exc)


@router.post("/logout", response_model=LogoutResponse)
def logout_endpoint(
    token: str = Depends(bearer_token),
    provider: AuthProvider = Depends(get_auth_provider),
) -> LogoutResponse:
    try:
        return logout(token, provider)
    except (InvalidCredentialsError, AuthProviderUnavailableError) as exc:
        _raise_auth_http_error(exc)
