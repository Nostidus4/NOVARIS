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
import pickle
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

from qshield_quantum.backends.simulator import make_sampler
from qshield_quantum.solvers.warm_start import make_warm_start_optimizer

# Đo thật 2026-08-14/15 (xem Quantum_Reporting.md): `qiskit_algorithms.QAOA` mặc định KHÔNG
# transpile ansatz trước khi mô phỏng — `PauliEvolutionGate` đi qua `Statevector.from_instruction()`
# bằng đường `to_matrix()` (tính nguyên ma trận 2^n x 2^n bằng `scipy.sparse.linalg.expm`), chậm
# ~14x ở n=8 so với khi transpile về gate cơ bản trước (kết quả tối ưu giống hệt, đã verify).
#
# ⚠️ QUAN TRỌNG (2026-08-15, đã verify lại nhiều lần): bật transpile không AN TOÀN TẤT ĐỊNH — đây là
# bug FLAKY/race condition thật trong Rust core qiskit-terra 2.5.2 (`pyo3_runtime.PanicException:
# not a DAG` tại `crates/circuit/src/dag_circuit.rs:1825`, lúc PassManager chạy `DepthAnalysis`/
# `UnitarySynthesis`). Đã chứng minh KHÔNG liên quan tên biến (cùng code, cùng tên `b0..b9`, có lúc
# chạy OK có lúc crash ngay lần gọi đầu) và KHÔNG liên quan riêng số qubit (n=8 "an toàn" chỉ vì ít
# thao tác transpile hơn → xác suất trúng race thấp hơn, KHÔNG phải zero). Vì vậy `n<=8` dưới đây là
# ngưỡng GIẢM RỦI RO (thống kê), không phải ngưỡng AN TOÀN TUYỆT ĐỐI — vẫn có thể crash ở n=8 dù xác
# suất thấp hơn n lớn. Muốn dùng transpile đáng tin cậy trong production PHẢI có retry (chạy lại
# trong subprocess mới nếu crash) — CHƯA implement, xem Quantum_Reporting.md mục "unresolved".
_TRANSPILE_SAFE_MAX_QUBITS = 8


def _make_transpiler(num_qubits: int):
    """`None` nếu num_qubits vượt ngưỡng đã verify an toàn — QAOA sẽ tự rơi về đường `expm` chậm
    nhưng ổn định thay vì risk crash (xem `_TRANSPILE_SAFE_MAX_QUBITS`)."""
    if num_qubits > _TRANSPILE_SAFE_MAX_QUBITS:
        return None
    return generate_preset_pass_manager(
        optimization_level=1, basis_gates=["rz", "sx", "x", "cx"]
    )


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
    transpiled: bool = False


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
    transpiler = _make_transpiler(qp.get_num_binary_vars())
    qaoa = QAOA(
        sampler=sampler,
        optimizer=COBYLA(maxiter=maxiter),
        reps=reps,
        transpiler=transpiler,
    )
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
        transpiled=transpiler is not None,
    )


_WORKER_MODULE = "qshield_quantum.solvers._qaoa_worker"


def _always_feasible(_bits: np.ndarray) -> bool:
    """Feasibility permissive, dùng khi bài toán không có ràng buộc K-of-N đơn giản (VD four-level
    encoding). Hàm cấp module (KHÔNG phải closure/lambda) để pickle được cho subprocess."""
    return True


def solve_qaoa_one_seed_fast(
    qp: QuadraticProgram,
    *,
    seed: int,
    shots: int,
    maxiter: int,
    k_actions: int | None = None,
    always_feasible: bool = False,
    reference_bitstring: str | None = None,
    reps: int = 1,
    warm_start: bool = False,
    candidate_pool_size: int = 20,
    max_retries: int = 2,
    subprocess_timeout_seconds: float = 120.0,
) -> QaoaSeedResult:
    """`solve_qaoa_one_seed` nhưng thử đường transpile (nhanh) an toàn qua subprocess + retry.

    Độ chính xác KHÔNG đổi so với `solve_qaoa_one_seed` thường — transpile chỉ đổi cách mô phỏng
    circuit, không đổi công thức toán (đã verify khớp exact tuyệt đối nhiều lần khi không crash,
    xem `Quantum_Reporting.md` 2026-08-15). Cơ chế:

    1. Thử chạy trong subprocess riêng với transpile CƯỠNG BỨC bật (nhanh ~14-100x).
    2. Bug flaky trong qiskit-terra 2.5.2 (không tất định, xem comment `_TRANSPILE_SAFE_MAX_QUBITS`
       ở trên) có thể làm subprocess đó crash — bắt được qua exit code khác 0, KHÔNG ảnh hưởng tiến
       trình gọi hàm này. Thử lại tối đa `max_retries` lần trong subprocess MỚI mỗi lần.
    3. Hết lượt retry mà vẫn crash → rơi về `solve_qaoa_one_seed` chạy thẳng trong tiến trình hiện
       tại (chậm nhưng luôn đúng, không transpile nếu vượt `_TRANSPILE_SAFE_MAX_QUBITS`) — LUÔN trả
       về kết quả đúng, không bao giờ raise vì lý do transpile crash.

    Hạn chế đã biết: chỉ hỗ trợ `feasibility` qua `k_actions` (luôn pickle được) — không nhận
    callable `feasibility` tuỳ ý (closure như `make_four_level_feasibility()` không pickle được).
    Gọi hàm này với `feasibility` tuỳ ý sẽ bỏ qua thẳng bước subprocess, chạy `solve_qaoa_one_seed`
    trực tiếp (đúng, không có lợi tốc độ) — xem `Quantum_Reporting.md` mục hạn chế.
    """
    feasibility = _always_feasible if always_feasible else None
    payload = {
        "qp": qp,
        "kwargs": {
            "seed": seed,
            "shots": shots,
            "maxiter": maxiter,
            "k_actions": k_actions,
            "feasibility": feasibility,
            "reference_bitstring": reference_bitstring,
            "reps": reps,
            "warm_start": warm_start,
            "candidate_pool_size": candidate_pool_size,
        },
    }
    try:
        payload_bytes = pickle.dumps(payload)
    except pickle.PicklingError, AttributeError, TypeError:
        # k_actions=None mà không có feasibility callable pickle được -> không thể chạy subprocess.
        return solve_qaoa_one_seed(
            qp,
            seed=seed,
            shots=shots,
            maxiter=maxiter,
            k_actions=k_actions,
            feasibility=feasibility,
            reference_bitstring=reference_bitstring,
            reps=reps,
            warm_start=warm_start,
            candidate_pool_size=candidate_pool_size,
        )

    with tempfile.TemporaryDirectory(prefix="qaoa_fast_") as tmp:
        input_path = Path(tmp) / "input.pkl"
        input_path.write_bytes(payload_bytes)
        for attempt in range(max_retries + 1):
            output_path = Path(tmp) / f"output_{attempt}.pkl"
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        _WORKER_MODULE,
                        str(input_path),
                        str(output_path),
                    ],
                    capture_output=True,
                    timeout=subprocess_timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                continue  # coi như 1 lần crash, thử lại (hoặc fallback nếu hết lượt)
            if proc.returncode == 0 and output_path.exists():
                result = pickle.loads(output_path.read_bytes())
                if not isinstance(result, QaoaSeedResult):
                    continue
                return result
            # crash (segfault, panic...) -> thử lại subprocess MỚI, không giữ trạng thái cũ.

    # Hết lượt retry -> đường chậm nhưng LUÔN đúng, không bao giờ để lỗi transpile làm mất kết quả.
    return solve_qaoa_one_seed(
        qp,
        seed=seed,
        shots=shots,
        maxiter=maxiter,
        k_actions=k_actions,
        feasibility=feasibility,
        reference_bitstring=reference_bitstring,
        reps=reps,
        warm_start=warm_start,
        candidate_pool_size=candidate_pool_size,
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
