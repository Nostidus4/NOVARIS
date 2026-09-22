# Supabase (workflow snapshots)

Backend đã có `SUPABASE_*` trong `backend/.env`. Pipeline vẫn ghi artifact ra đĩa; bước sync đẩy bản tóm tắt JSON lên Postgres để API đọc lại.

## 1. Tạo bảng (một lần)

Supabase Dashboard → **SQL Editor** → dán nội dung:

`backend/supabase/migrations/001_workflow_snapshots.sql`

→ **Run**.

## 2. Sync artifact → DB

```bash
# từ root repo, API đang chạy hoặc gọi Python trực tiếp:
curl -X POST http://127.0.0.1:8000/workflow/sync

# hoặc
cd backend && uv run python -c "
from qshield_api.config import get_config
from qshield_api.infrastructure.persistence.workflow_repository_impl import FileWorkflowRepository
from qshield_api.infrastructure.persistence.supabase_workflow_store import sync_workflow_snapshot
print(sync_workflow_snapshot(get_config(), FileWorkflowRepository(get_config()).get_summary()))
"
```

## 3. Đọc

`GET /workflow/summary` ưu tiên hàng mới nhất trong `workflow_snapshots` (theo `run_key`); nếu DB lỗi/thiếu thì fallback file trên đĩa.

Biến môi trường (tùy chọn, trong `backend/.env`):

```
QSHIELD_WORKFLOW_STORE=supabase   # supabase | file  (mặc định: supabase)
```

## 4. Email/password authentication

API đăng nhập dùng Supabase Auth, không dùng bảng `workflow_snapshots` và không lưu mật khẩu trong
Q-SHIELD.

1. Mở Supabase Dashboard → **Authentication → Providers → Email** và bật Email provider.
   Bật **Allow new users to sign up** để dùng trang `/register`.
2. Tạo user tại **Authentication → Users → Add user**, hoặc dùng luồng invite của Supabase.
3. Nếu đang test local, chạy backend ở `http://127.0.0.1:8000` và frontend ở
   `http://localhost:3000`.
4. Đăng ký tại `/register`, đăng nhập tại `/login`; API tương ứng là
   `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, và `POST /auth/logout`.
5. Nếu **Confirm email** đang bật, người dùng phải mở liên kết Supabase gửi qua email trước khi
   đăng nhập. Nếu tắt, đăng ký thành công sẽ tạo session và vào console ngay.

Giao diện hiện chỉ hỗ trợ email/password và không hiển thị social login.
