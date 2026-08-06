# Đỗ Ngọc Tân - CỔNG CHẶN bắt buộc: so 3 cách tính objective (NumPy thuần, QuadraticProgram, QUBO sau convert) trước khi tin bất kỳ kết quả QAOA nào.
"""Cổng chặn bắt buộc (CLAUDE.md quy tắc 15): so 3 cách tính objective trên TOÀN BỘ 2⁸=256
bitstring (rẻ với 8 qubit, không có lý do gì chỉ lấy mẫu — `plan.md` câu hỏi 8).

1. `formulation.objective.objective_batch` — NumPy thuần, ground truth.
2. `QuadraticProgram.objective.evaluate` — từ `formulation.qiskit_program.build_quadratic_program`.
3. `QUBO.objective.evaluate` sau `QuadraticProgramToQubo` — từ `formulation.qiskit_program.to_qubo`.

Lệch ở bất kỳ bitstring nào ⇒ dừng, sửa `formulation/`, đừng debug QAOA khi QUBO còn sai
(CLAUDE.md: "Đừng debug QAOA khi QUBO còn sai").
"""

from __future__ import annotations

import itertools

import numpy as np

from qshield_quantum.formulation.objective import objective_batch
from qshield_quantum.formulation.qiskit_program import build_quadratic_program, to_qubo
from qshield_quantum.formulation.qubo import build_qubo
from qshield_quantum.formulation.surrogate import QuadraticSurrogate


class ConsistencyError(ValueError):
    """Raise khi 3 cách tính objective lệch nhau — không tin bất kỳ QAOA nào cho tới khi sửa xong."""


def all_bitstrings(n: int) -> np.ndarray:
    """Toàn bộ `2**n` tổ hợp nhị phân, shape `(2**n, n)` — dùng chung cho exact solver."""
    return np.array(list(itertools.product([0, 1], repeat=n)), dtype=int)


def bitstring_chunks(n: int, chunk_size: int = 65_536):
    """Yield all binary states in stable lexicographic/integer order without full allocation."""
    if not 1 <= n <= 62:
        raise ValueError(f"n must be in [1, 62] for uint64 enumeration, got {n}.")
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}.")
    shifts = np.arange(n - 1, -1, -1, dtype=np.uint64)
    for start in range(0, 1 << n, chunk_size):
        integers = np.arange(start, min(start + chunk_size, 1 << n), dtype=np.uint64)
        yield ((integers[:, None] >> shifts) & 1).astype(np.int8)


def verify_quadratic_consistency(
    model: QuadraticSurrogate,
    *,
    variable_names: list[str],
    atol: float = 1e-6,
    chunk_size: int = 65_536,
) -> None:
    """Compare NumPy, QuadraticProgram, and converted QUBO for every generic state."""
    if len(variable_names) != model.dimension:
        raise ValueError(
            f"variable_names has {len(variable_names)} entries, expected {model.dimension}."
        )
    qp = build_quadratic_program(
        model.Q, model.linear, model.constant, ticker_order=variable_names
    )
    qubo = to_qubo(qp)
    checked = 0
    for Z in bitstring_chunks(model.dimension, chunk_size):
        numpy_energy = model.evaluate_batch(Z)
        qp_energy = np.fromiter(
            (qp.objective.evaluate(z) for z in Z), dtype=float, count=len(Z)
        )
        qubo_energy = np.fromiter(
            (qubo.objective.evaluate(z) for z in Z), dtype=float, count=len(Z)
        )
        mismatch_qp = np.flatnonzero(np.abs(numpy_energy - qp_energy) > atol)
        mismatch_qubo = np.flatnonzero(np.abs(numpy_energy - qubo_energy) > atol)
        if len(mismatch_qp) or len(mismatch_qubo):
            local = int(mismatch_qp[0] if len(mismatch_qp) else mismatch_qubo[0])
            bits = "".join(str(int(bit)) for bit in Z[local])
            raise ConsistencyError(
                "verify_quadratic_consistency FAIL at "
                f"z={bits}: numpy={numpy_energy[local]:.12g}, "
                f"qp={qp_energy[local]:.12g}, qubo={qubo_energy[local]:.12g}."
            )
        checked += len(Z)
    if checked != 1 << model.dimension:
        raise ConsistencyError(
            f"Consistency enumeration checked {checked}, expected {1 << model.dimension} states."
        )


def verify_consistency(
    g: np.ndarray,
    C: np.ndarray,
    c: np.ndarray,
    *,
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
    ticker_order: list[str],
    atol: float = 1e-6,
) -> None:
    n = g.shape[0]
    Z = all_bitstrings(n)

    energies_numpy = objective_batch(
        Z,
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )

    Q, linear, constant = build_qubo(
        g,
        C,
        c,
        lambda_1=lambda_1,
        lambda_2=lambda_2,
        penalty=penalty,
        k_actions=k_actions,
    )
    qp = build_quadratic_program(Q, linear, constant, ticker_order=ticker_order)
    qubo = to_qubo(qp)

    energies_qp = np.array([qp.objective.evaluate(z) for z in Z])
    energies_qubo = np.array([qubo.objective.evaluate(z) for z in Z])

    mismatches_qp = np.where(np.abs(energies_numpy - energies_qp) > atol)[0]
    mismatches_qubo = np.where(np.abs(energies_numpy - energies_qubo) > atol)[0]

    if len(mismatches_qp) or len(mismatches_qubo):
        lines = [
            (
                f"verify_consistency FAIL — {len(mismatches_qp)} bitstring lệch với "
                f"QuadraticProgram, {len(mismatches_qubo)} lệch với QUBO sau convert "
                f"(trên tổng {len(Z)} bitstring)."
            )
        ]
        for idx in mismatches_qp[:5]:
            bits = "".join(str(b) for b in Z[idx])
            lines.append(
                f"  z={bits}: numpy={energies_numpy[idx]:.6f} qp={energies_qp[idx]:.6f}"
            )
        for idx in mismatches_qubo[:5]:
            bits = "".join(str(b) for b in Z[idx])
            lines.append(
                f"  z={bits}: numpy={energies_numpy[idx]:.6f} qubo={energies_qubo[idx]:.6f}"
            )
        raise ConsistencyError("\n".join(lines))
