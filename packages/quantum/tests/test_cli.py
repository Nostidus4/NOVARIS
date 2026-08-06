# Đỗ Ngọc Tân - smoke test CLI `qshield-quantum solve --mock`: artifact ra đủ, đúng schema.
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from qshield_contracts.enums import SolverKind
from qshield_contracts.schemas.optimization import QaoaResult, validate_qaoa_result
from qshield_quantum.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def _write_config(tmp_path: Path, **overrides) -> Path:
    """Config phẳng (không `includes`) — n=4 mã để exact (2^4) + QAOA (4 qubit, 10 seed) chạy
    nhanh trong test, không cần đúng 8 mã thật của `configs/universe.yaml`."""
    config = {
        "seed": 20260805,
        "artifacts": {"mode": "dev", "root": str(tmp_path / "artifacts")},
        "tickers": [{"ticker": name} for name in ("AAA", "BBB", "CCC", "DDD")],
        "k_actions": 2,
        "cvar_alpha": 0.95,
        "penalty": {"lambda_1": None, "lambda_2": None, "P": None},
        "qaoa": {"shots": 64, "optimizer_maxiter": 10, "min_seeds": 10, "seeds": None},
        "backend": "simulator",
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
