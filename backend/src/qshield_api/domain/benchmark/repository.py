# Đỗ Ngọc Tân - Protocol BenchmarkRepository.
from __future__ import annotations

from typing import Protocol

from qshield_api.domain.benchmark.entities import BenchmarkView


class BenchmarkRepository(Protocol):
    def get_benchmark(self) -> BenchmarkView | None: ...
