# Đỗ Ngọc Tân - hạ tầng kết nối Supabase, cài đặt sẵn để dùng sau.
#
# TRẠNG THÁI: setup only — CHƯA được wiring vào bất kỳ router/dependency nào trong routers/ hay
# deps.py. Đừng import module này ở nơi khác cho đến khi có quyết định dưới đây.
#
# Q-SHIELD hiện KHÔNG có khái niệm user/login. `docs/product/mvp_scope.md` mục "NGOÀI PHẠM VI"
# (OOS-013) liệt kê rõ: "Public multi-user authentication, billing và broker integration — Không
# cần cho competition prototype." Trước khi dùng client này để bật auth/RLS trên bất kỳ route nào,
# cần Product Owner (Nguyễn Thị Ánh Ngọc) xác nhận đây là thay đổi phạm vi hợp lệ, theo quy trình
# Change Request ở `docs/product/mvp_scope.md` §22.
#
# Secret key (`SUPABASE_SECRET_KEY`) có quyền bypass Row Level Security — chỉ dùng ở phía server,
# không bao giờ trả về response hay log ra ngoài. Đọc từ biến môi trường (`backend/.env`, đã
# gitignore), không hard-code trong code hay commit vào repo (CLAUDE.md NFR-019 / PR-NFR-SEC-003).

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client


class SupabaseSettings(BaseSettings):
    """Đọc cấu hình Supabase từ biến môi trường (`SUPABASE_*`) — không hard-code secret trong code."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SUPABASE_", extra="ignore")

    url: str
    publishable_key: str
    secret_key: str
    jwks_url: str


@lru_cache
def get_supabase_settings() -> SupabaseSettings:
    return SupabaseSettings()


@lru_cache
def get_supabase_client() -> Client:
    """Client phía server, dùng secret key — chỉ gọi từ backend, không bao giờ expose ra frontend."""
    settings = get_supabase_settings()
    return create_client(settings.url, settings.secret_key)
