# Đỗ Ngọc Tân - khởi tạo FastAPI app, đăng ký routers.
"""Đăng ký thủ công (khác `app/modules/*` auto-discovery ở repo tham khảo `architecture.md`
§5 — Q-SHIELD chưa từng có auto-discovery, không phải thứ mới ở đây). 7 router — path/method giữ
nguyên `docs/architecture/pipeline.md`.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from qshield_api.interfaces.api.routers import (
    benchmark,
    console,
    optimize,
    portfolio,
    regime,
    risk,
    runs,
    scenarios,
    workflow,
)

app = FastAPI(
    title="Q-SHIELD API",
    description="Chỉ đọc artifact / gọi qshield_risk/qshield_quantum — không chứa công thức "
    "tài chính (CLAUDE.md quy tắc 9).",
)

# Origin browser được phép gọi API (Sync / Run optimize từ console).
# Thêm qua env `QSHIELD_CORS_ORIGINS` (comma-separated), ví dụ:
#   QSHIELD_CORS_ORIGINS=https://nostidus4.github.io,https://novaris.example.com
_DEFAULT_CORS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "https://nostidus4.github.io",
]
_EXTRA_CORS = [
    origin.strip()
    for origin in os.getenv("QSHIELD_CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*_DEFAULT_CORS, *_EXTRA_CORS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router)
app.include_router(regime.router)
app.include_router(scenarios.router)
app.include_router(risk.router)
app.include_router(optimize.router)
app.include_router(benchmark.router)
app.include_router(runs.router)
app.include_router(workflow.router)
app.include_router(console.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
