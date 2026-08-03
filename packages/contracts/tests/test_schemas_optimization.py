# Đỗ Ngọc Tân - test validate_qaoa_result: đúng K bit, tối thiểu 10 seed (spec đi trước packages/quantum).
import pytest
from qshield_contracts.enums import SolverKind
from qshield_contracts.schemas.optimization import QaoaResult, validate_qaoa_result


def _make_result(**overrides) -> QaoaResult:
    base = {
        "bitstring": "10100000",
        "k_actions": 2,
        "chosen_actions": [0, 2],
        "requested_solver": SolverKind.QAOA,
        "actual_solver": SolverKind.QAOA,
        "exact_energy": -1.5,
        "qaoa_energy_by_seed": {i: -1.4 - 0.01 * i for i in range(10)},
        "optimality_gap": 0.05,
        "feasibility_rate": 0.9,
        "true_cvar_before": 0.05,
        "true_cvar_after": 0.03,
        "shots": 1024,
        "backend": "simulator",
        "runtime_seconds": 1.2,
    }
    base.update(overrides)
    return QaoaResult(**base)


def test_valid_result_passes() -> None:
    validate_qaoa_result(_make_result())  # không raise


def test_bitstring_bit_count_mismatch_fails() -> None:
    result = _make_result(bitstring="11100000")  # 3 bit=1, k_actions=2
    with pytest.raises(ValueError, match="bitstring"):
        validate_qaoa_result(result)


def test_too_few_seeds_fails() -> None:
    result = _make_result(qaoa_energy_by_seed={0: -1.4, 1: -1.3})
    with pytest.raises(ValueError, match="seed"):
        validate_qaoa_result(result)
