# Đỗ Ngọc Tân - smoke test CLI `qshield-quantum solve --mock`: artifact ra đủ, đúng schema.
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from qshield_contracts.enums import SolverKind
from qshield_contracts.schemas.optimization import QaoaResult, validate_qaoa_result
from qshield_quantum.cli import app
from typer.testing import CliRunner

runner = CliRunner()
_TEST_TICKERS = ("AAA", "BBB", "CCC", "DDD")
# `qshield_risk.portfolio.validate_ticker_order` hiện kỳ vọng 8 mã trên một số fixture test —
# đường evaluate() dùng bộ 8 mã dưới; path --mock/QUBO thuần dùng `_TEST_TICKERS` (n=4).
_RISK_TEST_TICKERS = ("ACB", "CTG", "VCB", "HPG", "VIC", "MWG", "VNM", "FPT")


def _write_config(tmp_path: Path, **overrides) -> Path:
    """Config phẳng (không `includes`) — n=4 mã để exact (2^4) + QAOA (4 qubit, 10 seed) chạy
    nhanh trong test, không cần đúng 8 mã thật của `configs/base.yaml`."""
    config = {
        "seed": 20260805,
        "artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")},
        "tickers": [{"ticker": name} for name in _TEST_TICKERS],
        "k_actions": 2,
        "cvar_alpha": 0.95,
        "penalty": {"lambda_1": None, "lambda_2": None, "P": None},
        "qaoa": {"shots": 64, "optimizer_maxiter": 10, "min_seeds": 10, "seeds": None},
        "backend": "simulator",
        # Chỉ path solve() không-mock (qua qshield_risk.evaluate) mới đọc tới các khóa dưới đây —
        # có sẵn ở mọi test cho gọn, không ảnh hưởng path --mock (thoát sớm trước khi tới đây).
        "action_reduction_pct": 0.20,
        "transaction_cost": {
            "fee": 0.001,
            "spread": 0.001,
            "liquidity_penalty": 0.0005,
        },
        "weight_sum_tolerance": 1e-9,
        "horizon_days": 5,
    }
    config.update(overrides)
    path = tmp_path / "test.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def _qaoa_result_from_payload(payload: dict) -> QaoaResult:
    return QaoaResult(
        bitstring=payload["bitstring"],
        k_actions=payload["k_actions"],
        chosen_actions=payload["chosen_actions"],
        requested_solver=SolverKind(payload["requested_solver"]),
        actual_solver=SolverKind(payload["actual_solver"]),
        exact_energy=payload["exact_energy"],
        qaoa_energy_by_seed={
            int(k): v for k, v in payload["qaoa_energy_by_seed"].items()
        },
        optimality_gap=payload["optimality_gap"],
        feasibility_rate=payload["feasibility_rate"],
        true_cvar_before=payload["true_cvar_before"],
        true_cvar_after=payload["true_cvar_after"],
        shots=payload["shots"],
        backend=payload["backend"],
        runtime_seconds=payload["runtime_seconds"],
    )


def _write_real_risk_and_scenario_fixtures(
    tmp_path: Path, tickers: tuple[str, ...], *, num_scenarios: int = 50
) -> None:
    """Ghi artifact `risk`/`scenarios` tối thiểu để `solve()` không-`--mock` chạy được đường thật
    (`qshield_risk.evaluate`), không cần chạy `packages/data`/`ai`/`risk` thật — tương tự cách
    `packages/pipeline` test mock từng chặng qua monkeypatch, nhưng ở đây cần dữ liệu THẬT trên đĩa
    vì `solve()` tự đọc file, không nhận tham số tiêm vào."""
    horizon = 5
    n = len(tickers)
    weights = {ticker: 1.0 / n for ticker in tickers}

    scenarios_dir = tmp_path / "artifacts" / "dev" / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260805)
    cube = rng.normal(0.0, 0.01, size=(num_scenarios, horizon, n))
    np.savez(scenarios_dir / "stress_scenarios.npz", scenarios=cube)
    (scenarios_dir / "scenario_manifest.json").write_text(
        json.dumps(
            {
                "gate_status": "PASS",
                "ticker_order": list(tickers),
                "num_scenarios": num_scenarios,
                "horizon_days": horizon,
            }
        ),
        encoding="utf-8",
    )

    risk_dir = tmp_path / "artifacts" / "dev" / "risk"
    risk_dir.mkdir(parents=True, exist_ok=True)
    (risk_dir / "action_effects.csv").write_text(
        "action_id,ticker,g,c\n"
        + "\n".join(
            f"{i},{ticker},{0.01 + 0.001 * i},{0.0005}"
            for i, ticker in enumerate(tickers)
        ),
        encoding="utf-8",
    )
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    (risk_dir / "pairwise_effects.csv").write_text(
        "action_i,action_j,C_ij\n"
        + "\n".join(f"{i},{j},{0.001 * (i + j)}" for i, j in pairs),
        encoding="utf-8",
    )
    (risk_dir / "baseline_risk.json").write_text(
        json.dumps(
            {
                "var_0": 0.02,
                "cvar_0": 0.03,
                "portfolio_weights": weights,
                "cash_weight": 0.0,
                "alpha": 0.95,
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.slow
def test_solve_real_scores_true_cvar_via_qshield_risk(tmp_path: Path) -> None:
    """`solve()` không `--mock` phải chấm lại true CVaR bằng `qshield_risk.evaluate()` thật (quy
    tắc 17) — không còn `NotImplementedError`. Subprocess + timeout cùng lý do đã giải thích ở
    test `--mock` phía trên (bẫy qiskit đã verify). Dùng đúng 8 mã (`_RISK_TEST_TICKERS`), không
    dùng bộ 4 mã rút gọn — `qshield_risk.portfolio.validate_ticker_order` hard-code 8."""
    config_path = _write_config(
        tmp_path,
        tickers=[{"ticker": name} for name in _RISK_TEST_TICKERS],
        k_actions=3,
    )
    _write_real_risk_and_scenario_fixtures(tmp_path, _RISK_TEST_TICKERS)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from qshield_quantum.cli import app; app()",
            "solve",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    stage_dir = tmp_path / "artifacts" / "dev" / "optimization"
    payload = json.loads((stage_dir / "qaoa_result.json").read_text(encoding="utf-8"))
    assert payload["true_cvar_before"] == payload["true_cvar_before"]  # không NaN
    assert payload["true_cvar_after"] == payload["true_cvar_after"]  # không NaN
    assert isinstance(payload["true_cvar_before"], float)
    assert isinstance(payload["true_cvar_after"], float)
    validate_qaoa_result(_qaoa_result_from_payload(payload))


@pytest.mark.slow
def test_solve_mock_writes_valid_qaoa_result_and_metrics(tmp_path: Path) -> None:
    """Chạy qua SUBPROCESS thật (`python -m qshield_quantum.cli` tương đương `uv run
    qshield-quantum solve`), không phải `CliRunner` trong tiến trình pytest.

    ⚠️ Lý do: qiskit 2.5.1 (`_accelerate.abi3.so`, Rust `CircuitData` drop) có thể treo
    `Py_FinalizeEx` sau nhiều seed QAOA (bug đã verify bằng `sample <pid>`, xem
    `qshield_quantum/cli.py::_fast_exit_if_standalone`). Chạy subprocess + `timeout=` ở đây vừa
    kiểm chứng đúng bản sửa `os._exit()` hoạt động thật (không chỉ trong tiến trình pytest, nơi
    `PYTEST_CURRENT_TEST` tắt hẳn `os._exit`), vừa không làm treo chính pytest nếu môi trường máy
    chạy test có dính lại bug đó.
    """
    config_path = _write_config(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from qshield_quantum.cli import app; app()",
            "solve",
            "--config",
            str(config_path),
            "--mock",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    stage_dir = tmp_path / "artifacts" / "dev" / "optimization"
    result_path = stage_dir / "qaoa_result.json"
    assert result_path.exists()
    assert (stage_dir / "benchmark.json").exists()

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert sum(int(b) for b in payload["bitstring"]) == payload["k_actions"] == 2
    assert len(payload["qaoa_energy_by_seed"]) >= 10
    assert payload["backend"] == "simulator"
    validate_qaoa_result(_qaoa_result_from_payload(payload))  # đúng schema thật

    # metrics.json sống ở run_root (= artifacts/dev/ ở dev mode), KHÔNG phải trong thư mục con
    # theo stage — xem ArtifactPaths.run_root/RunContext.write_metrics.
    metrics = json.loads(
        (tmp_path / "artifacts" / "dev" / "metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["penalty_is_provisional"] is True
    assert metrics["gate_status"] == "PASS"


def test_solve_without_mock_and_without_risk_fails_clearly(tmp_path: Path) -> None:
    """Test nhanh, trong tiến trình (KHÔNG chạm QAOA — thoát sớm trước verify/exact/qaoa nên
    không có rủi ro treo ở trên), giữ `CliRunner` cho gọn."""
    config_path = _write_config(tmp_path)
    result = runner.invoke(app, ["solve", "--config", str(config_path)])
    assert result.exit_code != 0
    assert "packages/risk" in result.output
