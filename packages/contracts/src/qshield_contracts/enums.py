# Đỗ Ngọc Tân - định nghĩa RegimeName, Stage, SolverKind, ArtifactMode (StrEnum) — ép kiểu ở __post_init__ trước khi so sánh, không so sánh bằng `is`.
#
# Bẫy đã dính một lần ở paths.py (xem docs/runbook/troubleshooting.md §2):
#   ArtifactMode("dev") == ArtifactMode.DEV   # đúng
#   "dev" is ArtifactMode.DEV                  # SAI — StrEnum so sánh bằng `is` không đáng tin.
# Luôn ép kiểu bằng constructor (`ArtifactMode(value)`) ở biên rồi mới so sánh bằng `==`.

from enum import StrEnum


class RegimeName(StrEnum):
    """Nhãn trạng thái thị trường.

    Gán SAU khi fit HMM, dựa trên đặc trưng thống kê (return/volatility/drawdown) của từng state —
    KHÔNG theo state id. HMM trả state 0/1/2 theo thứ tự ngẫu nhiên tùy seed; giả định
    "state 0 = NORMAL" là bug im lặng (CLAUDE.md quy tắc 7).
    """

    NORMAL = "normal"
    VOLATILE = "volatile"
    STRESS = "stress"


class ArtifactMode(StrEnum):
    """Chế độ ghi artifact — xem `configs/base.yaml` (`artifacts.mode`) và `paths.py` (ArtifactPaths)."""

    DEV = "dev"    # artifacts/dev/... — đường dẫn cố định, lặp nhanh khi phát triển
    RUNS = "runs"  # artifacts/runs/run_YYYYMMDD_HHMM/... — có version, bắt buộc từ ngày 4 sprint


class Stage(StrEnum):
    """6 chặng của pipeline, đúng thứ tự chạy — xem docs/architecture/pipeline.md §2 và stages.py."""

    DATA = "data"
    REGIME = "regime"
    SCENARIOS = "scenarios"
    RISK = "risk"
    QUBO = "qubo"
    SOLVE = "solve"


class SolverKind(StrEnum):
    """Solver THỰC TẾ đã tạo ra một kết quả.

    Luôn ghi actual_solver bên cạnh requested_solver trong artifact/run manifest — nếu QAOA
    timeout/fail và hệ thống fallback về exact/classical, actual_solver phải phản ánh đúng cái đã
    thực sự chạy, không phải cái người dùng yêu cầu (xem docs/runbook/troubleshooting.md §5).
    """

    EXACT = "exact"
    QAOA = "qaoa"
    CLASSICAL = "classical"
