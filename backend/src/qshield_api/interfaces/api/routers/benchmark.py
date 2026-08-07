# Đỗ Ngọc Tân - GET /benchmark/quantum-vs-classical — đọc artifact benchmark, không tự tính lại.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from qshield_api.application.benchmark.dto import BenchmarkDTO
from qshield_api.application.benchmark.use_cases.get_benchmark import get_benchmark
from qshield_api.deps import get_benchmark_repository
from qshield_api.domain.benchmark.repository import BenchmarkRepository

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.get("/quantum-vs-classical", response_model=BenchmarkDTO)
def get_benchmark_endpoint(
    repo: BenchmarkRepository = Depends(get_benchmark_repository),
) -> BenchmarkDTO:
    dto = get_benchmark(repo)
    if dto is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Chưa có workflow_benchmark.json / benchmark.json — chạy "
                "`qshield-quantum workflow --exact-only` (hoặc solve demo_fast) trước."
            ),
        )
    return dto
