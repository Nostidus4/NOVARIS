# backend/

**Owner:** Đỗ Ngọc Tân
**Vai trò:** FastAPI — đọc artifact / orchestration job; **không** chứa công thức tài chính.
**Stack:** hexagonal — `interfaces` → `application` → `domain` ← `infrastructure`.

## Nhiệm vụ

- REST API cho dashboard (regime, scenarios, risk, quantum, portfolio, runs, optimize, workflow…).
- Đọc artifact qua `ArtifactPaths` / persistence adapter.
- Chạy optimize/pipeline bằng job runner (subprocess), không nhúng solver trong router.
- OpenAPI → frontend `yarn types` (nếu có script).

## Cây chính

```text
qshield_api/
  main.py, config.py, deps.py
  interfaces/api/          # routers
  application/             # use-cases
  domain/                  # ports + pure domain (không CVaR formula)
  infrastructure/          # persistence, jobs, runner, calculation adapters
```

## Được làm

- Validate request/response.
- Map artifact → DTO cho UI.
- Ghi nhận `requested_solver` / `actual_solver` / fallback trung thực.

## Không được làm

- Một dòng tính CVaR / VaR / QUBO trong `routers/` hoặc application (CLAUDE quy tắc 9).
- Đọc portfolio mẫu global khi request user có portfolio riêng (workflow-v2 §9).
- Nối chuỗi path artifact.

## Context cho Claude

```bash
uv run uvicorn qshield_api.main:app --reload --port 8000
```

- Sau đổi schema response: `cd frontend && yarn types` (nếu có script).
- Optimize production: bỏ equal-weight hidden path (workflow-v2 §9, §21 P0).
- Hexagonal: infrastructure implements ports; domain không import FastAPI.

## Test

```bash
uv run pytest backend -q
```
