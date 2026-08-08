# Q-SHIELD Frontend

NOVARIS Q-SHIELD Risk Intelligence Console (Next.js 15/16 + Tailwind 4).

## Run

```bash
# API (repo root)
uv run uvicorn qshield_api.main:app --reload --port 8000

# Frontend (Yarn — không dùng npm install)
cd frontend && yarn install && yarn dev
```

Docker (FE + BE):

```bash
docker compose up --build
# UI http://localhost:3000 · API http://localhost:8000/health
```

Environment:

- `QSHIELD_API_URL` — server-side fetch (default `http://127.0.0.1:8000`).
- `NEXT_PUBLIC_QSHIELD_API_URL` — browser-side fetch cho các nút ghi/chạy job. Cùng default.
  Origin của frontend phải nằm trong `allow_origins` của CORS ở `backend/src/qshield_api/main.py`.

## Pages

| Route | API |
|---|---|
| `/overview` | `GET /console/overview` |
| `/data` | `GET /console/data` |
| `/regime` | `GET /console/regime` |
| `/scenarios` | `GET /console/scenarios` |
| `/risk` | `GET /console/risk` |
| `/quantum` | `GET /console/quantum` |
| `/report` | `GET /console/report` |
| layout shell | `GET /console/shell` |

## Nút có tác dụng gì

Console không tính lại số tài chính (CLAUDE.md quy tắc 9/10). Mỗi nút chỉ làm đúng một việc:

| Nút | Hành vi |
|---|---|
| Refresh (mọi trang) | `router.refresh()` — đọc lại artifact qua `/console/*` |
| Sync to Supabase (Overview) | `POST /workflow/sync` — đẩy snapshot hiện tại lên database |
| Run optimization (Quantum) | `POST /optimize/jobs` rồi poll `GET /optimize/jobs/{id}` |
| Download package / Export (Report) | Ghi ra file JSON từ payload đang hiển thị |
| Copy (log panel) | Chép các dòng log đang lọc vào clipboard |
| Run selector (topbar) | Popover metadata lần chạy đang xem |
| Theme toggle | Đổi sáng/tối, lưu vào `localStorage` |

Bảng ở Risk / Quantum / Data / Scenarios sort + lọc + tìm kiếm phía client trên chính dữ liệu
backend trả về; không có phép tính tài chính nào chạy ở đây.

UI shell matches `NOVARIS_QSHIELD_Host3000.html`.

## Deploy GitHub Pages

```bash
# Build giống CI (sinh frontend/out, basePath /NOVARIS)
cd frontend && yarn build:pages
```

Workflow: `.github/workflows/deploy-pages.yml` — push `main`/`master` hoặc Run workflow thủ công.
Settings → Pages → Source = **GitHub Actions**.

Nếu không có API public, CI tự bật backend tạm ở chế độ `file`, đọc artifact đã commit và bake
số liệu vào HTML tĩnh. Các nút ghi/chạy runtime (Sync, Optimize) vẫn cần
`NEXT_PUBLIC_QSHIELD_API_URL` trỏ đến backend public.
