# GitHub Pages — NOVARIS Q-SHIELD console
#
# Workflow: `.github/workflows/deploy-pages.yml`
# Site (project Pages): https://nostidus4.github.io/NOVARIS/
#
# ---------------------------------------------------------------------------
# Bật Pages (một lần)
# ---------------------------------------------------------------------------
#
# 1. Repo Settings → Pages → Build and deployment → Source = **GitHub Actions**
# 2. Push lên `main` (hoặc Actions → "Deploy GitHub Pages" → Run workflow)
# 3. Đợi job xanh; URL nằm ở environment **github-pages**
#
# ---------------------------------------------------------------------------
# Build local giống CI
# ---------------------------------------------------------------------------
#
#   cd frontend
#   GITHUB_PAGES=true npm run build          # → frontend/out/
#   # hoặc
#   npm run build:pages
#
# Xem thử tĩnh (basePath /NOVARIS):
#
#   npx --yes serve out -p 4173
#   open http://127.0.0.1:4173/NOVARIS/overview/
#
# ---------------------------------------------------------------------------
# Secrets / biến (Settings → Secrets and variables → Actions)
# ---------------------------------------------------------------------------
#
# | Secret                        | Vai trò                                              |
# |-------------------------------|------------------------------------------------------|
# | `QSHIELD_API_URL`             | Fetch lúc **build** để bake số liệu vào HTML         |
# | `NEXT_PUBLIC_QSHIELD_API_URL` | URL API nhúng vào JS cho nút Sync / Run optimize     |
# | `NEXT_BASE_PATH`              | Override; mặc định `/NOVARIS`. `root` hoặc `/` = ""  |
#
# Backend public phải cho CORS origin `https://nostidus4.github.io`
# (đã có trong `backend/src/qshield_api/main.py`) hoặc set
# `QSHIELD_CORS_ORIGINS`.
#
# ---------------------------------------------------------------------------
# Giới hạn (đọc trước khi kỳ vọng “live dashboard”)
# ---------------------------------------------------------------------------
#
# - Pages = static. Không host FastAPI.
# - Nếu không set `QSHIELD_API_URL`, workflow tự bật FastAPI tạm với
#   `QSHIELD_WORKFLOW_STORE=file`, đọc artifact đã commit và bake số liệu vào
#   HTML. API tạm bị tắt ngay sau build.
# - Server Component chỉ gọi API lúc CI build, không poll lại mỗi lần user F5
#   trừ khi rebuild. Nút client (Sync, Optimize, Refresh) vẫn cần backend public
#   qua `NEXT_PUBLIC_QSHIELD_API_URL` và CORS đúng.
# - Không commit `.env` chứa secret; chỉ dùng GitHub Secrets.
#
# ---------------------------------------------------------------------------
# Troubleshooting
# ---------------------------------------------------------------------------
#
# **"Failed to build /overview ... took more than 60 seconds" (retry 3 lần rồi fail)**
#
# Server Component gọi API lúc build. Nếu `QSHIELD_API_URL` là chuỗi rỗng thì
# `fetch("/console/overview")` thành URL tương đối và treo cả build.
# `frontend/lib/api.ts` xử lý sẵn: chuỗi rỗng = chưa cấu hình → bỏ qua fetch,
# và mọi fetch có timeout 15s. Nếu vẫn gặp, kiểm tra secret có khoảng trắng thừa.
#
# Tái hiện tại máy:
#
#   cd frontend
#   GITHUB_PAGES=true QSHIELD_API_URL= npm run build      # phải xong ~10s, HTML offline
#   GITHUB_PAGES=true QSHIELD_API_URL=http://127.0.0.1:8000 npm run build   # bake số liệu
#
