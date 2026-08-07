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
