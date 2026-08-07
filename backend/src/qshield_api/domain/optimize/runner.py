# Đỗ Ngọc Tân - Protocol OptimizeRunner — port quan trọng nhất, BẮT BUỘC implement qua subprocess.
"""`run()` thuần: nhận `job_id` (để cô lập output — xem §4a design doc), trả `OptimizeResult` hoặc
raise. Config đọc từ `self.cfg` (tiêm qua constructor lúc khởi tạo implementation, giống các port
khác — xem `deps.py`), không cần tham số path riêng. KHÔNG tự cập nhật `OptimizeJobRepository` bên
trong — việc chuyển trạng thái `queued → running → done|failed` thuộc về nơi gọi
(`application/optimize/use_cases/submit_job.py::run_job`), để `OptimizeRunner` chỉ có một trách
nhiệm duy nhất: chạy `qshield-quantum solve` và trả kết quả.

Implementation THẬT (`infrastructure/runner/subprocess_optimize_runner.py`) bắt buộc gọi qua
subprocess — xem docs/architecture/backend_hexagonal_design.md §3: import `qshield_quantum` trực
tiếp trong tiến trình `qshield_api` đã verify là sẽ segfault (qiskit + pyarrow chung tiến trình).
"""

from __future__ import annotations

from typing import Protocol

from qshield_api.domain.optimize.entities import OptimizeResult


class OptimizeRunner(Protocol):
    def run(self, job_id: str) -> OptimizeResult: ...
