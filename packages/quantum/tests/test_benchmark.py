# Đỗ Ngọc Tân - greedy_classical_baseline + build_benchmark: đúng công thức, không tự tuyên bố quantum advantage.
import numpy as np
import pytest
from qshield_quantum.benchmark import build_benchmark, greedy_classical_baseline
from qshield_quantum.solvers.exact import ExactResult
from qshield_quantum.solvers.qaoa import QaoaSeedResult


def test_greedy_classical_baseline_picks_top_k_by_g() -> None:
    g = np.array([1.0, 5.0, 2.0, 4.0])
    C = np.zeros((4, 4))
    c = np.zeros(4)

    bitstring, energy = greedy_classical_baseline(
        g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=50.0, k_actions=2
    )

    assert bitstring == "0101"  # index 1, 3 — g lớn nhất
    assert energy == pytest.approx(-(5.0 + 4.0))


def _seed_result(
    seed: int, bitstring: str, energy: float, feasible: bool
) -> QaoaSeedResult:
    return QaoaSeedResult(
        seed=seed,
        bitstring=bitstring,
        energy=energy,
        feasible=feasible,
        feasibility_rate=1.0 if feasible else 0.0,
        success_prob=0.5,
        runtime_seconds=0.01,
    )


def test_build_benchmark_picks_lowest_energy_feasible_seed() -> None:
    exact = ExactResult(
        best_feasible_bitstring="0101",
        best_feasible_energy=-9.0,
        best_overall_bitstring="0111",
        best_overall_energy=-11.0,
        all_energies={},
        evaluated_states=16,
    )
    qaoa_by_seed = {
        0: _seed_result(0, "0101", -9.0, True),
        1: _seed_result(1, "1010", -3.0, True),
        2: _seed_result(
            2, "0111", -11.0, False
        ),  # năng lượng thấp hơn nhưng INFEASIBLE
    }
    g = np.array([1.0, 5.0, 2.0, 4.0])
    C = np.zeros((4, 4))
    c = np.zeros(4)

    bench = build_benchmark(
        exact,
        qaoa_by_seed,
        g=g,
        C=C,
        c=c,
        lambda_1=1.0,
        lambda_2=1.0,
        penalty=50.0,
        k_actions=2,
    )

    assert (
        bench["winning_bitstring"] == "0101"
    )  # seed 2 rẻ hơn nhưng bị loại vì infeasible
    assert bench["winning_is_feasible"] is True
    assert bench["n_seeds_feasible"] == 2
    assert bench["n_seeds_total"] == 3
    assert bench["optimality_gap"] == pytest.approx(0.0)  # trùng đúng nghiệm exact
    assert "caveat" in bench
    assert isinstance(bench["qaoa_beats_classical"], bool)


def test_build_benchmark_raises_on_empty_seed_dict() -> None:
    exact = ExactResult("01", -1.0, "01", -1.0, {}, 4)
    with pytest.raises(ValueError, match="rỗng"):
        build_benchmark(
            exact,
            {},
            g=np.zeros(2),
            C=np.zeros((2, 2)),
            c=np.zeros(2),
            lambda_1=1.0,
            lambda_2=1.0,
            penalty=1.0,
            k_actions=1,
        )


def test_build_generic_benchmark_allows_empty_qaoa_when_non_final() -> None:
    from qshield_quantum.benchmark import build_generic_benchmark
    from qshield_quantum.formulation.surrogate import QuadraticSurrogate
    from qshield_quantum.solvers.exact import ExactCandidate, GenericExactResult

    model = QuadraticSurrogate(
        Q=np.zeros((2, 2)),
        linear=np.array([0.1, -0.2]),
        constant=0.0,
        residual_sum_squares=0.0,
        rank=2,
        sample_count=4,
    )
    exact = GenericExactResult(
        best_feasible_bitstring="01",
        best_feasible_energy=-0.2,
        best_overall_bitstring="01",
        best_overall_energy=-0.2,
        top_feasible_candidates=(ExactCandidate(bitstring="01", energy=-0.2),),
        evaluated_states=4,
        feasible_states=1,
    )
    bench = build_generic_benchmark(
        exact,
        {},
        model=model,
        allow_non_final=True,
        NON_FINAL_CONFIG=True,
        requested_solver="qaoa",
        actual_solver="exact",
        fallback_reason="QAOA skipped",
        classical_restarts=4,
        classical_seed=0,
    )
    assert bench["qaoa_seed_count"] == 0
    assert bench["actual_solver"] == "exact"
    assert bench["requested_solver"] == "qaoa"
    assert bench["success_prob"] is None
    assert "classical_bitstring" in bench


def test_build_generic_benchmark_one_seed_non_final() -> None:
    from qshield_quantum.benchmark import build_generic_benchmark
    from qshield_quantum.formulation.surrogate import QuadraticSurrogate
    from qshield_quantum.solvers.exact import ExactCandidate, GenericExactResult

    model = QuadraticSurrogate(
        Q=np.zeros((2, 2)),
        linear=np.array([0.1, -0.2]),
        constant=0.0,
        residual_sum_squares=0.0,
        rank=2,
        sample_count=4,
    )
    exact = GenericExactResult(
        best_feasible_bitstring="01",
        best_feasible_energy=-0.2,
        best_overall_bitstring="01",
        best_overall_energy=-0.2,
        top_feasible_candidates=(ExactCandidate(bitstring="01", energy=-0.2),),
        evaluated_states=4,
        feasible_states=1,
    )
    qaoa = {
        101: _seed_result(101, "01", -0.2, True),
    }
    bench = build_generic_benchmark(
        exact,
        qaoa,
        model=model,
        minimum_seeds=1,
        allow_non_final=True,
        classical_restarts=4,
        classical_seed=0,
    )
    assert bench["n_seeds_total"] == 1
    assert bench["success_prob"] == pytest.approx(0.5)
    assert "best" in bench["energy_stats"]
    assert bench["requested_solver"] == "qaoa"
    assert bench["actual_solver"] == "qaoa"
