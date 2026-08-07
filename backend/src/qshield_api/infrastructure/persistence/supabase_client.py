# Đỗ Ngọc Tân - hạ tầng kết nối Supabase.
#
# Dùng để LƯU / ĐỌC snapshot artifact (workflow_snapshots) — KHÔNG dùng cho auth/login.
# Auth/RLS multi-user vẫn ngoài phạm vi MVP (OOS-013, docs/product/mvp_scope.md).
#
# Secret key (`SUPABASE_SECRET_KEY`) bypass Row Level Security — chỉ server-side.
# Đọc từ `backend/.env` (gitignore), không hard-code (CLAUDE.md NFR-019).

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from supabase import Client, create_client

_BACKEND_DIR = Path(__file__).resolve().parents[4]  # .../backend
_ENV_FILE = _BACKEND_DIR / ".env"


class SupabaseSettings(BaseSettings):
    """Đọc cấu hình Supabase từ biến môi trường (`SUPABASE_*`)."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.is_file() else ".env",
        env_prefix="SUPABASE_",
        extra="ignore",
    )

    url: str
    publishable_key: str
    secret_key: str
    jwks_url: str


@lru_cache
def get_supabase_settings() -> SupabaseSettings:
    return SupabaseSettings()


@lru_cache
def get_supabase_client() -> Client:
    """Client phía server, dùng secret key — không expose ra frontend."""
    settings = get_supabase_settings()
    return create_client(settings.url, settings.secret_key)
