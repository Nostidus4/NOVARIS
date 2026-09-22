import pytest

from qshield_api.domain.auth.provider import (
    InvalidCredentialsError,
    RegistrationError,
)
from qshield_api.infrastructure.auth.local_auth_provider import LocalAuthProvider


def test_local_registration_returns_an_immediate_verifiable_session() -> None:
    provider = LocalAuthProvider()

    registration = provider.register(
        email="USER@example.com",
        password="strong-password",
        display_name="Local User",
    )

    assert registration.email_confirmation_required is False
    assert registration.session is not None
    assert registration.user.email == "user@example.com"
    assert (
        provider.get_user(registration.session.access_token).display_name
        == "Local User"
    )


def test_local_user_can_login_and_logout() -> None:
    provider = LocalAuthProvider()
    provider.register("user@example.com", "strong-password", "Local User")

    session = provider.login("user@example.com", "strong-password")
    provider.logout(session.access_token)

    with pytest.raises(InvalidCredentialsError):
        provider.get_user(session.access_token)


def test_local_provider_rejects_duplicate_email_and_wrong_password() -> None:
    provider = LocalAuthProvider()
    provider.register("user@example.com", "strong-password", "Local User")

    with pytest.raises(RegistrationError):
        provider.register("USER@example.com", "another-password", "Duplicate")
    with pytest.raises(InvalidCredentialsError):
        provider.login("user@example.com", "wrong-password")
