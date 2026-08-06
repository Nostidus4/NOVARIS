# Đỗ Ngọc Tân - thoát nhanh cuối session test — xem ghi chú chi tiết trong solvers/qaoa.py, cli.py.
"""⚠️ **Bẫy kỹ thuật đã verify** (qua `sample <pid>`, không suy đoán): qiskit 2.5.1
(`_accelerate.abi3.so`, Rust `CircuitData` drop) có thể làm tiến trình pytest **segfault khi
`Py_FinalizeEx` chạy** — LUÔN xảy ra SAU KHI toàn bộ test đã chạy xong và kết quả (`N passed`) đã
in ra, không ảnh hưởng tới tính đúng đắn của bất kỳ test nào. Vấn đề duy nhất: exit code của
`pytest` bị segfault (139) ghi đè lên exit code thật (0 nếu mọi test pass), khiến CI hiểu nhầm là
job fail dù test xanh hết.

`pytest_unconfigure` chạy SAU CÙNG — sau `pytest_sessionfinish` của `TerminalReporter` (hook in
dòng tổng kết "N passed in Xs") — gọi `os._exit()` với đúng exit code thật TẠI ĐÂY để bỏ qua hoàn
toàn `Py_FinalizeEx`, đồng thời không cắt mất dòng tổng kết (đã thử `pytest_sessionfinish` trước:
hook đó chạy TRƯỚC `TerminalReporter` in tổng kết trong cùng sự kiện `pytest_sessionfinish`, nên
`os._exit()` ở đó cắt mất dòng "N passed in Xs" dù exit code vẫn đúng). `os._exit()` cũng bỏ qua
flush stdio bình thường — khi output bị pipe (không phải tty), Python block-buffer stdout, nên vẫn
phải flush thủ công trước khi thoát dù đã đợi tới `pytest_unconfigure`. Tương tự cách
`qshield_quantum/cli.py::_fast_exit_if_standalone` xử lý cho CLI thật.
"""

import os
import sys

_exitstatus: int | None = None


def pytest_sessionfinish(exitstatus: int) -> None:
    global _exitstatus
    _exitstatus = int(exitstatus)


def pytest_unconfigure() -> None:
    # `_exitstatus` chỉ được set nếu `pytest_sessionfinish` đã thực sự chạy (một session test
    # hoàn chỉnh). Nếu `None` (vd. lỗi ngay lúc parse argument, trước khi có session) — để tiến
    # trình thoát bình thường, không giả vờ exit code 0.
    if _exitstatus is None:
        return
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_exitstatus)
