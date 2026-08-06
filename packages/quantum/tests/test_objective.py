# Đỗ Ngọc Tân - test objective.objective: khớp tính tay + objective_batch nhất quán với objective.
import numpy as np
from qshield_quantum.formulation.objective import objective, objective_batch


def test_objective_matches_hand_computed_value() -> None:
    z = np.array([1, 0, 1])
    g = np.array([1.0, 2.0, 3.0])
    C = np.array([[0.0, 0.5, 0.0], [0.5, 0.0, 0.0], [0.0, 0.0, 0.0]])
    c = np.array([0.1, 0.1, 0.1])

    # -g'z = -(1+3) = -4
    # z'Cz = z0*C00*z0 + z0*C01*z1 + ... = 2*0.5*z0*z1 = 2*0.5*1*0 = 0 (z1=0)
    # c'z = 0.1+0.1 = 0.2
    # penalty*(sum(z)-k)^2 = 10*(2-2)^2 = 0
    value = objective(z, g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=10.0, k_actions=2)
    assert value == -4.0 + 0.0 + 0.2 + 0.0


def test_objective_penalty_punishes_infeasible_count() -> None:
    g = np.zeros(3)
    C = np.zeros((3, 3))
    c = np.zeros(3)
    z_feasible = np.array([1, 1, 0])
    z_infeasible = np.array([1, 0, 0])

    e_feasible = objective(
        z_feasible, g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=10.0, k_actions=2
    )
    e_infeasible = objective(
        z_infeasible, g, C, c, lambda_1=1.0, lambda_2=1.0, penalty=10.0, k_actions=2
    )
    assert e_feasible == 0.0
    assert e_infeasible == 10.0  # penalty*(1-2)^2


def test_objective_batch_matches_loop_over_objective() -> None:
    rng = np.random.default_rng(0)
    n = 5
    g = rng.normal(size=n)
    C = rng.normal(size=(n, n))
    C = (C + C.T) / 2
    np.fill_diagonal(C, 0.0)
    c = np.abs(rng.normal(size=n))

    Z = rng.integers(0, 2, size=(20, n))
    batch = objective_batch(
        Z, g, C, c, lambda_1=0.7, lambda_2=1.3, penalty=5.0, k_actions=2
    )
    looped = np.array(
        [
            objective(z, g, C, c, lambda_1=0.7, lambda_2=1.3, penalty=5.0, k_actions=2)
            for z in Z
        ]
    )
    assert np.allclose(batch, looped)
