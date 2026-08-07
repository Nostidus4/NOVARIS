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
# - Server Component chỉ gọi API lúc CI build, không poll lại mỗi lần user F5
#   trừ khi rebuild. Nút client (Sync, Optimize, Refresh) thì gọi API runtime
#   nếu `NEXT_PUBLIC_QSHIELD_API_URL` trỏ đúng và CORS mở.
# - Không commit `.env` chứa secret; chỉ dùng GitHub Secrets.
#
