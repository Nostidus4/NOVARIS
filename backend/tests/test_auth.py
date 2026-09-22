from fastapi.testclient import TestClient

from qshield_api.deps import get_auth_provider
from qshield_api.domain.auth.entities import AuthRegistration, AuthSession, AuthUser
from qshield_api.domain.auth.provider import (
    AuthProviderUnavailableError,
    InvalidCredentialsError,
    RegistrationError,
)
from qshield_api.main import app


class _FakeAuthProvider:
    def login(self, email: str, password: str) -> AuthSession:
        if email == "offline@example.com":
            raise AuthProviderUnavailableError
        if password != "correct-password":
            raise InvalidCredentialsError
        user = AuthUser(id="user-123", email=email, display_name="Q Shield")
        return AuthSession(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_in=3600,
            expires_at=1_800_000_000,
            user=user,
        )

    def register(
        self, email: str, password: str, display_name: str
    ) -> AuthRegistration:
        if email == "offline@example.com":
            raise AuthProviderUnavailableError
        if email == "existing@example.com":
            raise RegistrationError
        user = AuthUser(id="new-user", email=email, display_name=display_name)
        if email == "confirm@example.com":
            return AuthRegistration(
                user=user, session=None, email_confirmation_required=True
            )
        session = AuthSession(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            expires_in=3600,
            expires_at=1_800_000_000,
            user=user,
        )
        return AuthRegistration(
            user=user, session=session, email_confirmation_required=False
        )

    def get_user(self, access_token: str) -> AuthUser:
        if access_token != "access-token":
            raise InvalidCredentialsError
        return AuthUser(
            id="user-123", email="user@example.com", display_name="Q Shield"
        )

    def logout(self, access_token: str) -> None:
        if access_token != "access-token":
            raise InvalidCredentialsError


def _client() -> TestClient:
    app.dependency_overrides[get_auth_provider] = _FakeAuthProvider
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_login_returns_normalized_session() -> None:
    response = _client().post(
        "/auth/login",
        json={"email": "USER@EXAMPLE.COM", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
        "expires_in": 3600,
        "expires_at": 1_800_000_000,
        "user": {
            "id": "user-123",
            "email": "user@example.com",
            "display_name": "Q Shield",
        },
    }


def test_login_maps_invalid_credentials_to_generic_401() -> None:
    response = _client().post(
        "/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Email hoặc mật khẩu không chính xác."


def test_login_maps_provider_failure_to_503() -> None:
    response = _client().post(
        "/auth/login",
        json={"email": "offline@example.com", "password": "correct-password"},
    )

    assert response.status_code == 503
    assert "tạm thời gián đoạn" in response.json()["detail"]


def test_register_returns_session_when_email_confirmation_is_disabled() -> None:
    response = _client().post(
        "/auth/register",
        json={
            "display_name": "New User",
            "email": "NEW@EXAMPLE.COM",
            "password": "strong-password",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["display_name"] == "New User"
    assert body["access_token"] == "new-access-token"
    assert body["email_confirmation_required"] is False


def test_register_supports_email_confirmation_flow() -> None:
    response = _client().post(
        "/auth/register",
        json={
            "display_name": "Confirm User",
            "email": "confirm@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 201
    assert response.json()["access_token"] is None
    assert response.json()["email_confirmation_required"] is True


def test_register_maps_rejected_request_to_safe_400() -> None:
    response = _client().post(
        "/auth/register",
        json={
            "display_name": "Existing User",
            "email": "existing@example.com",
            "password": "strong-password",
        },
    )

    assert response.status_code == 400
    assert "Không thể tạo tài khoản" in response.json()["detail"]


def test_me_requires_a_well_formed_bearer_header() -> None:
    assert _client().get("/auth/me").status_code == 401
    assert (
        _client().get("/auth/me", headers={"Authorization": "Basic abc"}).status_code
        == 401
    )


def test_me_returns_current_user_for_valid_token() -> None:
    response = _client().get(
        "/auth/me", headers={"Authorization": "Bearer access-token"}
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "user@example.com"


def test_logout_is_callable_with_valid_token() -> None:
    response = _client().post(
        "/auth/logout", headers={"Authorization": "Bearer access-token"}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Đã đăng xuất."}
