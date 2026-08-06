# Đỗ Ngọc Tân - QAOA p=1, 1024 shots, COBYLA, tối thiểu 10 seed — không cherry-pick seed.
"""QAOA p=1 thường (KHÔNG warm-start ở lần đầu — `plan.md` câu hỏi 2: `solvers/warm_start.py` là
tùy chọn theo `docs/Structure.md`, và với 8 qubit bài toán đủ nhỏ để không cần warm-start mới hội
tụ; thêm sau nếu benchmark cho thấy cần).

API đã verify khớp `docs/runbook/troubleshooting.md` §2 — `qiskit.primitives.Sampler` (V1) đã bị
xóa khỏi qiskit 2.x, PHẢI dùng `StatevectorSampler`.

Chạy TOÀN BỘ seed trong danh sách, không cherry-pick (CLAUDE.md quy tắc 18 / `docs/limitations.md`
§4: "không được cherry-pick seed tốt nhất").
"""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass

from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

from qshield_quantum.backends.simulator import make_sampler


@dataclass(frozen=True)
class QaoaSeedResult:
    seed: int
    bitstring: str
    energy: float
    feasible: bool
    feasibility_rate: float  # tổng xác suất đo được của các sample thỏa Σz=K
    success_prob: (
        float  # xác suất đo được đúng `reference_bitstring` (thường = nghiệm exact)
    )
    runtime_seconds: float


def _bitstring_of(x) -> str:
    return "".join(str(round(b)) for b in x)


def solve_qaoa_one_seed(
    qp: QuadraticProgram,
    *,
    seed: int,
    shots: int,
    maxiter: int,
    k_actions: int,
    reference_bitstring: str | None = None,
) -> QaoaSeedResult:
    t0 = time.perf_counter()
    sampler = make_sampler(shots=shots, seed=seed)
    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=1)
    result = MinimumEigenOptimizer(qaoa).solve(qp)
    runtime = time.perf_counter() - t0

    bitstring = _bitstring_of(result.x)
    feasibility_rate = float(
        sum(s.probability for s in result.samples if round(sum(s.x)) == k_actions)
    )
    if reference_bitstring is not None:
        success_prob = float(
            sum(
                s.probability
                for s in result.samples
                if _bitstring_of(s.x) == reference_bitstring
            )
        )
    else:
        success_prob = float(max((s.probability for s in result.samples), default=0.0))

    return QaoaSeedResult(
        seed=seed,
        bitstring=bitstring,
        energy=float(result.fval),
        feasible=round(sum(result.x)) == k_actions,
        feasibility_rate=feasibility_rate,
        success_prob=success_prob,
        runtime_seconds=runtime,
    )


def solve_qaoa(
    qp: QuadraticProgram,
    *,
    seeds: list[int],
    shots: int,
    maxiter: int,
    k_actions: int,
    reference_bitstring: str | None = None,
) -> dict[int, QaoaSeedResult]:
    """Chạy TOÀN BỘ seed, trả `{seed: QaoaSeedResult}` đầy đủ — kể cả seed cho kết quả tệ.

    ⚠️ **Bẫy kỹ thuật đã verify** (qua `sample`/profiling, không phải suy đoán): qiskit 2.x
    (`qiskit_algorithms.QAOA` + `MinimumEigenOptimizer`) tạo nhiều đối tượng `CircuitData` (Rust,
    trong `_accelerate.abi3.so`) mỗi seed. Với ≥10 seed liên tiếp trong CÙNG tiến trình, garbage
    collector chu kỳ (cyclic GC) của Python có thể rơi vào vòng lặp cực kỳ chậm/treo khi giải
    phóng các đối tượng này giữa lúc chạy (100% CPU trong `gc_collect` → Rust `drop_glue` của
    `CircuitData`, xác nhận bằng `sample <pid>`). Tắt cyclic GC quanh vòng lặp (rồi khôi phục
    đúng trạng thái cũ) tránh được việc này — đối tượng vẫn được giải phóng qua refcounting bình
    thường, chỉ tắt phần thu gom chu trình định kỳ. Không phải bug của package này.
    """
    if len(seeds) < 10:
        raise ValueError(
            f"Chỉ có {len(seeds)} seed, cần tối thiểu 10 (CLAUDE.md quy tắc 18 / "
            "docs/limitations.md §4: không cherry-pick seed)."
        )
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        return {
            seed: solve_qaoa_one_seed(
                qp,
                seed=seed,
                shots=shots,
                maxiter=maxiter,
                k_actions=k_actions,
                reference_bitstring=reference_bitstring,
            )
            for seed in seeds
        }
    finally:
        if was_enabled:
            gc.enable()
