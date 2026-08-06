# Đỗ Ngọc Tân - solve_exact: đối chiếu tay trên bộ g/C/c nhỏ tự tạo, duyệt đủ 2^n trạng thái.
import numpy as np
from qshield_quantum.solvers.exact import solve_exact


def test_solve_exact_picks_highest_g_when_no_interaction() -> None:
    # g=[1,5,2,4], C=c=0, k_actions=2 -> feasible tốt nhất phải chọn index 1 và 3 (g lớn nhất)
    g = np.array([1.0, 5.0, 2.0, 4.0])
    C = np.zeros((4, 4))
    c = np.zeros(4)

    result = solve_exact(g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=50.0, k_actions=2)

    assert result.evaluated_states == 16
    assert result.best_feasible_bitstring == "0101"  # index 1 và 3 = '1'
    assert sum(int(b) for b in result.best_feasible_bitstring) == 2


def test_solve_exact_reports_all_256_energies_for_8_bit() -> None:
    rng = np.random.default_rng(5)
    n = 8
    g = rng.normal(size=n)
    raw = rng.normal(size=(n, n))
    C = (raw + raw.T) / 2
    np.fill_diagonal(C, 0.0)
    c = np.abs(rng.normal(size=n))

    result = solve_exact(g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=20.0, k_actions=3)

    assert result.evaluated_states == 256
    assert len(result.all_energies) == 256
    assert sum(int(b) for b in result.best_feasible_bitstring) == 3
    assert result.best_overall_energy <= result.best_feasible_energy


def test_solve_exact_raises_when_k_actions_impossible() -> None:
    import pytest

    g = np.zeros(2)
    C = np.zeros((2, 2))
    c = np.zeros(2)
    with pytest.raises(ValueError, match="Không có bitstring feasible"):
        solve_exact(g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=1.0, k_actions=5)
