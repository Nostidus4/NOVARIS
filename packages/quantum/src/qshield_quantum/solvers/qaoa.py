# Đỗ Ngọc Tân - QAOA p=1, 1024 shots, COBYLA, tối thiểu 10 seed — không cherry-pick seed.
"""QAOA p=1 thường (KHÔNG warm-start ở lần đầu — `plan.md` câu hỏi 2: `solvers/warm_start.py` là
tùy chọn theo `docs/Structure.md`, và với 8 qubit bài toán đủ nhỏ để không cần warm-start mới hội
tụ; thêm sau nếu benchmark cho thấy cần).

API đã verify khớp `docs/runbook/troubleshooting.md` §2 — `qiskit.primitives.Sampler` (V1) đã bị
xóa khỏi qiskit 2.x, PHẢI dùng `StatevectorSampler`.

Chạy TOÀN BỘ seed trong danh sách, không cherry-pick (CLAUDE.md quy tắc 18 / `docs/workflow-v2.md`
§16: "không được cherry-pick seed tốt nhất").
"""

from __future__ import annotations

import gc
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

from qshield_quantum.backends.simulator import make_sampler
from qshield_quantum.solvers.warm_start import make_warm_start_optimizer


@dataclass(frozen=True)
class QaoaSample:
    bitstring: str
    energy: float
    probability: float
    feasible: bool


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
    samples: tuple[QaoaSample, ...] = ()
    warm_start_used: bool = False


def _bitstring_of(x) -> str:
    return "".join(str(round(b)) for b in x)


def solve_qaoa_one_seed(
    qp: QuadraticProgram,
    *,
    seed: int,
    shots: int,
    maxiter: int,
    k_actions: int | None = None,
    reference_bitstring: str | None = None,
    feasibility: Callable[[np.ndarray], bool] | None = None,
    reps: int = 1,
    warm_start: bool = False,
    candidate_pool_size: int = 20,
) -> QaoaSeedResult:
    if k_actions is None and feasibility is None:
        raise ValueError("Provide k_actions or a generic feasibility predicate.")
    if reps < 1:
        raise ValueError(f"reps must be positive, got {reps}.")
    if candidate_pool_size < 1:
        raise ValueError(
            f"candidate_pool_size must be positive, got {candidate_pool_size}."
        )
    required_actions = k_actions
    is_feasible = feasibility or (
        lambda bits: int(np.rint(bits).sum()) == required_actions
    )
    t0 = time.perf_counter()
    sampler = make_sampler(shots=shots, seed=seed)
    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=reps)
    algorithm = make_warm_start_optimizer(qaoa) if warm_start else None
    warm_start_used = algorithm is not None
    result = (algorithm or MinimumEigenOptimizer(qaoa)).solve(qp)
    runtime = time.perf_counter() - t0

    if result.x is None:
        raise RuntimeError(f"QAOA seed={seed} returned no decision vector.")
    result_x = np.asarray(result.x)
    bitstring = _bitstring_of(result_x)
    result_energy = (
        float(result.fval)
        if result.fval is not None
        else float(qp.objective.evaluate(result_x))
    )
    samples = tuple(
        QaoaSample(
            bitstring=_bitstring_of(sample.x),
            energy=(
                float(sample.fval)
                if sample.fval is not None
                else float(qp.objective.evaluate(sample.x))
            ),
            probability=float(sample.probability),
            feasible=bool(is_feasible(np.asarray(sample.x))),
        )
        for sample in sorted(
            result.samples, key=lambda item: (item.fval, -item.probability)
        )[:candidate_pool_size]
    )
    feasibility_rate = float(
        sum(s.probability for s in result.samples if is_feasible(np.asarray(s.x)))
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
        energy=result_energy,
        feasible=bool(is_feasible(result_x)),
        feasibility_rate=feasibility_rate,
        success_prob=success_prob,
        runtime_seconds=runtime,
        samples=samples,
        warm_start_used=warm_start_used,
    )


def solve_qaoa(
    qp: QuadraticProgram,
    *,
    seeds: list[int],
    shots: int,
    maxiter: int,
    k_actions: int | None = None,
    reference_bitstring: str | None = None,
    feasibility: Callable[[np.ndarray], bool] | None = None,
    reps: int = 1,
    warm_start: bool = False,
    candidate_pool_size: int = 20,
    minimum_seeds: int = 10,
) -> dict[int, QaoaSeedResult]:
    """Chạy TOÀN BỘ seed, trả `{seed: QaoaSeedResult}` đầy đủ — kể cả seed cho kết quả tệ.

    Final/baseline runs keep ``minimum_seeds=10``. ``NON_FINAL_CONFIG`` may lower it, but must
    still run every seed in the provided list without cherry-picking.

    ⚠️ **Bẫy kỹ thuật đã verify** (qua `sample`/profiling, không phải suy đoán): qiskit 2.x
    (`qiskit_algorithms.QAOA` + `MinimumEigenOptimizer`) tạo nhiều đối tượng `CircuitData` (Rust,
    trong `_accelerate.abi3.so`) mỗi seed. Với ≥10 seed liên tiếp trong CÙNG tiến trình, garbage
    collector chu kỳ (cyclic GC) của Python có thể rơi vào vòng lặp cực kỳ chậm/treo khi giải
    phóng các đối tượng này giữa lúc chạy (100% CPU trong `gc_collect` → Rust `drop_glue` của
    `CircuitData`, xác nhận bằng `sample <pid>`). Tắt cyclic GC quanh vòng lặp (rồi khôi phục
    đúng trạng thái cũ) tránh được việc này — đối tượng vẫn được giải phóng qua refcounting bình
    thường, chỉ tắt phần thu gom chu trình định kỳ. Không phải bug của package này.
    """
    if minimum_seeds < 1:
        raise ValueError("minimum_seeds must be >= 1.")
    if len(seeds) < minimum_seeds:
        raise ValueError(
            f"Chỉ có {len(seeds)} seed, cần tối thiểu {minimum_seeds} "
            "(CLAUDE.md quy tắc 18 / docs/workflow-v2.md §16: không cherry-pick seed)."
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
                feasibility=feasibility,
                reps=reps,
                warm_start=warm_start,
                candidate_pool_size=candidate_pool_size,
            )
            for seed in seeds
        }
    finally:
        if was_enabled:
            gc.enable()
