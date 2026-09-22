"""Validated HTTP contracts for authentication."""

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=6, max_length=256)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=256)

    @field_validator("display_name", mode="after")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Tên hiển thị cần có ít nhất 2 ký tự.")
        return normalized

    @field_validator("email", mode="after")
    @classmethod
    def normalize_register_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class AuthUserDTO(BaseModel):
    id: str
    email: str
    display_name: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: int | None = None
    user: AuthUserDTO


class RegisterResponse(BaseModel):
    user: AuthUserDTO
    email_confirmation_required: bool
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    expires_at: int | None = None


class SessionResponse(BaseModel):
    user: AuthUserDTO


class LogoutResponse(BaseModel):
    message: str = "Đã đăng xuất."
