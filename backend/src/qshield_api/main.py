# Đỗ Ngọc Tân - khởi tạo FastAPI app, đăng ký routers.
"""Đăng ký thủ công (khác `app/modules/*` auto-discovery ở repo tham khảo `architecture.md`
§5 — Q-SHIELD chưa từng có auto-discovery, không phải thứ mới ở đây). 7 router — path/method giữ
nguyên `docs/architecture/pipeline.md`.
"""

from __future__ import annotations

from fastapi import FastAPI

from qshield_api.interfaces.api.routers import (
    benchmark,
    optimize,
    portfolio,
    regime,
    risk,
    runs,
    scenarios,
)

app = FastAPI(
    title="Q-SHIELD API",
    description="Chỉ đọc artifact / gọi qshield_risk/qshield_quantum — không chứa công thức "
    "tài chính (CLAUDE.md quy tắc 9).",
)

app.include_router(portfolio.router)
app.include_router(regime.router)
app.include_router(scenarios.router)
app.include_router(risk.router)
app.include_router(optimize.router)
app.include_router(benchmark.router)
app.include_router(runs.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
