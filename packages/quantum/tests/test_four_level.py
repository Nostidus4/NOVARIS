"""Focused tests for the generic four-level workflow branch."""

import itertools

import numpy as np
import pandas as pd
import pytest
from qshield_quantum import workflow as workflow_mod
from qshield_quantum.formulation.four_level import (
    decode_action_levels,
    encode_action_levels,
    four_level_bitstring,
    four_level_variable_names,
)
from qshield_quantum.formulation.surrogate import (
    QuadraticSurrogate,
    fit_quadratic_surrogate,
    quadratic_feature_count,
    structured_samples_to_arrays,
)
from qshield_quantum.solvers.exact import solve_quadratic_exact
from qshield_quantum.solvers.qaoa import QaoaSeedResult
from qshield_quantum.verify.consistency import verify_quadratic_consistency
from qshield_quantum.workflow import (
    FOUR_LEVEL_MODE,
    candidate_order_from_handoff,
    make_four_level_feasibility,
    run_four_level_workflow,
    validate_four_level_profile,
)


def _linear_model(dimension: int) -> QuadraticSurrogate:
    return QuadraticSurrogate(
        Q=np.zeros((dimension, dimension)),
        linear=-np.arange(1, dimension + 1, dtype=float),
        constant=3.0,
        residual_sum_squares=0.0,
        rank=quadratic_feature_count(dimension),
        sample_count=quadratic_feature_count(dimension),
    )


def test_four_level_codec_uses_profile_mapping() -> None:
    levels = [0, 10, 20, 30]
    assert four_level_bitstring(levels) == "00100111"
    assert encode_action_levels(levels).tolist() == [0, 0, 1, 0, 0, 1, 1, 1]
    assert decode_action_levels("00100111").tolist() == levels


def test_four_level_codec_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="Action levels"):
        encode_action_levels([5])
    with pytest.raises(ValueError, match="even bit count"):
        decode_action_levels("101")


def test_surrogate_recovers_quadratic_samples_from_bitstrings() -> None:
    dimension = 4
    Z = np.array(list(itertools.product([0, 1], repeat=dimension)), dtype=int)
    truth = QuadraticSurrogate(
        Q=np.array(
            [
                [0.0, 0.5, 0.0, -0.25],
                [0.5, 0.0, 0.75, 0.0],
                [0.0, 0.75, 0.0, 0.125],
                [-0.25, 0.0, 0.125, 0.0],
            ]
        ),
        linear=np.array([1.0, -2.0, 0.5, 3.0]),
        constant=-4.0,
        residual_sum_squares=0.0,
        rank=11,
        sample_count=16,
    )
    frame = pd.DataFrame(
        {
            "bitstring": ["".join(map(str, row)) for row in Z],
            "objective": truth.evaluate_batch(Z),
        }
    )
    bits, targets, target = structured_samples_to_arrays(frame, ["AAA", "BBB"])
    fitted = fit_quadratic_surrogate(bits, targets)
    assert target == "objective"
    np.testing.assert_allclose(
        fitted.evaluate_batch(Z), truth.evaluate_batch(Z), atol=1e-10
    )
    assert fitted.rank == quadratic_feature_count(dimension)


def test_surrogate_requires_full_rank_structured_samples() -> None:
    Z = np.zeros((11, 4), dtype=int)
    with pytest.raises(ValueError, match="rank deficient"):
        fit_quadratic_surrogate(Z, np.zeros(11))


def test_generic_consistency_matches_all_three_paths() -> None:
    model = _linear_model(6)
    verify_quadratic_consistency(
        model, variable_names=four_level_variable_names(["A", "B", "C"]), chunk_size=17
    )


def test_chunked_exact_evaluates_all_16_bit_states_without_energy_dict() -> None:
    model = _linear_model(16)
    result = solve_quadratic_exact(model, chunk_size=4096, top_n=7)
    assert result.evaluated_states == 65_536
    assert result.feasible_states == 65_536
    assert result.best_feasible_bitstring == "1" * 16
    assert len(result.top_feasible_candidates) == 7
    assert not hasattr(result, "all_energies")


@pytest.mark.slow
def test_chunked_exact_evaluates_optional_20_bit_reference() -> None:
    model = _linear_model(20)
    result = solve_quadratic_exact(model, chunk_size=65_536, top_n=3)
    assert result.evaluated_states == 1_048_576
    assert result.best_feasible_bitstring == "1" * 20


def test_generic_feasibility_and_profile_boundary() -> None:
    profile = {
        "quantum": {
            "mode": FOUR_LEVEL_MODE,
            "input_candidates": 2,
            "action_levels_pct": [0, 10, 20, 30],
            "bit_encoding": {"bits_per_asset": 2},
        }
    }
    assert validate_four_level_profile(profile)["input_candidates"] == 2
    predicate = make_four_level_feasibility(
        {"max_active_candidates": 1, "max_total_action_pct": 20}
    )
    assert predicate(encode_action_levels([20, 0]))
    assert not predicate(encode_action_levels([20, 10]))
    assert not predicate(encode_action_levels([30, 0]))

    candidates = pd.DataFrame(
        {
            "ticker": ["B", "A", "X"],
            "rank": [2, 1, 3],
            "selected_top10": [True, True, False],
        }
    )
    assert candidate_order_from_handoff(candidates, expected_candidates=2) == ["A", "B"]


def _four_level_handoff(tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Full-rank structured handoff (bitstring + objective) for `dimension = 2 * len(tickers)`,
    small enough (<=8 bits) to fit/verify/exact-solve instantly — reused by the P1-1 tests below
    to exercise `run_four_level_workflow` without a real QAOA run (QAOA itself is monkeypatched
    out; only the surrogate fit / verify / exact / classical-benchmark plumbing runs for real)."""
    dimension = 2 * len(tickers)
    Z = np.array(list(itertools.product([0, 1], repeat=dimension)), dtype=int)
    truth = _linear_model(dimension)
    frame = pd.DataFrame(
        {
            "bitstring": ["".join(map(str, row)) for row in Z],
            "objective": truth.evaluate_batch(Z),
        }
    )
    candidates = pd.DataFrame(
        {
            "ticker": tickers,
            "rank": list(range(1, len(tickers) + 1)),
            "selected_top10": [True] * len(tickers),
        }
    )
    return candidates, frame


def _four_level_profile(input_candidates: int) -> dict:
    return {
        "quantum": {
            "mode": FOUR_LEVEL_MODE,
            "input_candidates": input_candidates,
            "action_levels_pct": [0, 10, 20, 30],
            "bit_encoding": {
                "bits_per_asset": 2,
                "total_decision_bits": 2 * input_candidates,
            },
            "qaoa": {"p": 1},
        }
    }


def _stub_qaoa_seed_result(qp, *, seed: int, **_ignored) -> QaoaSeedResult:
    return QaoaSeedResult(
        seed=seed,
        bitstring="1" * qp.get_num_binary_vars(),
        energy=0.0,
        feasible=True,
        feasibility_rate=1.0,
        success_prob=1.0,
        runtime_seconds=0.001,
    )


def test_workflow_picks_fast_qaoa_with_always_feasible_when_constraints_empty(
    monkeypatch,
) -> None:
    """P1-1: `run_four_level_workflow` phải gọi `solve_qaoa_one_seed_fast` (đường transpile
    cưỡng bức qua subprocess, nhanh ~14-100x — `solve_qaoa_one_seed` thường không bao giờ hoàn
    thành ở 20-bit), KHÔNG phải `solve_qaoa_one_seed`. Khi `risk_summary["quantum_constraints"]`
    rỗng, phải dùng `always_feasible=True` (pickle-safe) — KHÔNG truyền closure `feasibility`."""
    tickers = ["AAA", "BBB"]
    candidates, samples = _four_level_handoff(tickers)
    profile = _four_level_profile(len(tickers))

    captured: list[dict] = []

    def _stub(qp, *, seed, shots, maxiter, **kwargs):
        captured.append(kwargs)
        return _stub_qaoa_seed_result(qp, seed=seed)

    monkeypatch.setattr(workflow_mod, "solve_qaoa_one_seed_fast", _stub)

    result = run_four_level_workflow(
        candidates,
        samples,
        profile=profile,
        risk_summary={"quantum_constraints": {}},
        seeds=[0],
        shots=8,
        maxiter=2,
        allow_non_final=True,
    )
    assert len(captured) == 1
    assert captured[0]["always_feasible"] is True
    assert "feasibility_constraints" not in captured[0]
    assert "feasibility" not in captured[0]  # không truyền closure qua kwargs của _fast
    assert result.benchmark["actual_solver"] == "qaoa"


def test_workflow_passes_constraints_dict_not_closure_when_constraints_present(
    monkeypatch,
) -> None:
    """P1-1: khi `quantum_constraints` phi rỗng, phải truyền dict THUẦN `feasibility_constraints`
    xuống `solve_qaoa_one_seed_fast` (worker tự dựng lại predicate bên trong subprocess) — KHÔNG
    cố pickle closure `make_four_level_feasibility(constraints)`. `subprocess_timeout_seconds`
    phải đọc từ `performance_budget.qaoa_seed_timeout_seconds`, không phải default 120.0 cứng."""
    tickers = ["AAA", "BBB"]
    candidates, samples = _four_level_handoff(tickers)
    profile = _four_level_profile(len(tickers))
    constraints = {"max_active_candidates": 1}

    captured: list[dict] = []

    def _stub(qp, *, seed, shots, maxiter, **kwargs):
        captured.append(kwargs)
        return _stub_qaoa_seed_result(qp, seed=seed)

    monkeypatch.setattr(workflow_mod, "solve_qaoa_one_seed_fast", _stub)

    result = run_four_level_workflow(
        candidates,
        samples,
        profile=profile,
        risk_summary={"quantum_constraints": constraints},
        seeds=[0],
        shots=8,
        maxiter=2,
        allow_non_final=True,
        performance_budget={"qaoa_seed_timeout_seconds": 42.0},
    )
    assert len(captured) == 1
    assert captured[0]["feasibility_constraints"] == constraints
    assert "always_feasible" not in captured[0]
    assert captured[0]["subprocess_timeout_seconds"] == 42.0
    assert result.benchmark["actual_solver"] == "qaoa"


def test_workflow_default_seed_timeout_falls_back_to_120s_when_budget_missing(
    monkeypatch,
) -> None:
    """Không có `performance_budget.qaoa_seed_timeout_seconds` -> giữ default cũ của `_fast`
    (120.0s), không truyền `None` xuống (subprocess.run(timeout=None) nghĩa là KHÔNG timeout)."""
    tickers = ["AAA", "BBB"]
    candidates, samples = _four_level_handoff(tickers)
    profile = _four_level_profile(len(tickers))

    captured: list[dict] = []

    def _stub(qp, *, seed, shots, maxiter, **kwargs):
        captured.append(kwargs)
        return _stub_qaoa_seed_result(qp, seed=seed)

    monkeypatch.setattr(workflow_mod, "solve_qaoa_one_seed_fast", _stub)

    run_four_level_workflow(
        candidates,
        samples,
        profile=profile,
        risk_summary={"quantum_constraints": {}},
        seeds=[0],
        shots=8,
        maxiter=2,
        allow_non_final=True,
        performance_budget={},
    )
    assert captured[0]["subprocess_timeout_seconds"] == 120.0


def test_workflow_records_fallback_instead_of_hanging_when_subprocess_gives_up(
    monkeypatch,
) -> None:
    """F.3: ở n>8 đường in-process KHÔNG transpile nên nó treo trong expm(2^n), không phải "chậm".

    Khi subprocess hết lượt retry, `solve_qaoa_one_seed_fast` phải raise
    `TranspileFallbackUnavailableError` và workflow phải ghi `fallback_reason` trung thực + chuyển
    sang exact — thay vì treo vô hạn (không artifact, không thông báo) hoặc để CLI chết.
    """
    from qshield_quantum.solvers.qaoa import TranspileFallbackUnavailableError

    def _always_gives_up(*_args, **_kwargs):
        raise TranspileFallbackUnavailableError("subprocess thất bại 3 lần ở 20 qubit")

    monkeypatch.setattr(workflow_mod, "solve_qaoa_one_seed_fast", _always_gives_up)

    tickers = ["AAA", "BBB"]
    candidates, samples = _four_level_handoff(tickers)
    profile = _four_level_profile(len(tickers))

    result = run_four_level_workflow(
        candidates,
        samples,
        profile=profile,
        risk_summary={"quantum_constraints": {}},
        seeds=[101, 202],
        shots=8,
        maxiter=1,
        warm_start=False,
        allow_non_final=True,
    )

    benchmark = result.benchmark
    assert result.qaoa_by_seed == {}, "không seed nào được ghi nhận là thành công"
    assert benchmark["actual_solver"] == "exact"
    assert benchmark["requested_solver"] == "qaoa"
    reason = str(benchmark["fallback_reason"])
    assert "seed=101" in reason and "20 qubit" in reason, (
        "fallback_reason phải chỉ đích danh seed và nguyên nhân, không chung chung"
    )


def test_exhaustive_budget_guard_rejects_bit_counts_over_the_approved_budget() -> None:
    """Dynamic-N (CR-WF2-005) có thể nâng N 10→15 để candidate gate PASS, thành 30 bit = 2^30.

    `bitstring_chunks` chấp nhận tới n=62 nên KHÔNG có gì báo lỗi — exact chỉ chạy ~78 phút rồi
    ăn hết RAM. Guard phải từ chối TRƯỚC khi bắt đầu, với ngưỡng suy từ ngân sách đã có trong
    config chứ không phải một con số tự đặt.
    """
    import typer
    from qshield_quantum.cli import _guard_exhaustive_budget

    budget = {"exact_timeout_seconds": 3600, "exact_states_per_second": 228_000}
    config = {"performance_budget": budget}

    _guard_exhaustive_budget(20, config)  # 2^20 ≈ 1,05e6 — thừa sức, không raise
    _guard_exhaustive_budget(28, config)  # 2^28 ≈ 2,7e8 — vẫn trong 8,2e8

    with pytest.raises(typer.BadParameter, match="30 decision bits"):
        _guard_exhaustive_budget(30, config)  # 2^30 ≈ 1,07e9 > 8,2e8

    # Thiếu khoá thông lượng ⇒ bỏ qua kiểm tra, KHÔNG tự đoán một ngưỡng.
    _guard_exhaustive_budget(
        30, {"performance_budget": {"exact_timeout_seconds": 3600}}
    )
    _guard_exhaustive_budget(30, {})


def test_peak_memory_uses_the_right_unit_for_this_platform() -> None:
    """P1-8 / plan E3: `peak_memory_mb` trước đây LUÔN null — schema có, validate có, không ai ghi.

    Bẫy đã dính một lần trong chính đợt review này: `ru_maxrss` trả BYTE trên macOS nhưng
    KILOBYTE trên Linux. Dùng sai hệ số cho ra "207 GiB" cho một tiến trình dùng 208 MB. Test
    kẹp giá trị vào một khoảng hợp lý cho tiến trình pytest — sai đơn vị 1024 lần sẽ rơi ra ngoài.
    """
    from qshield_quantum.cli import _peak_memory_mb

    peak = _peak_memory_mb()
    assert peak > 10.0, f"{peak} MB quá nhỏ — nhiều khả năng chia dư 1024 lần"
    assert peak < 200_000.0, (
        f"{peak} MB quá lớn — nhiều khả năng thiếu một lần chia 1024"
    )


def test_reference_hardware_detects_machine_but_owner_values_win() -> None:
    """Không có cpu/os thì `runtime_seconds` giữa hai máy không so được — mà đó là mục đích
    của benchmark. Giá trị owner ghi đè trong config phải thắng giá trị tự dò."""
    from qshield_quantum.cli import _reference_hardware

    auto = _reference_hardware({})
    assert auto["cpu"], "phải dò được cpu"
    assert auto["os"], "phải dò được os"
    assert auto["cpu_count"] == __import__("os").cpu_count()

    overridden = _reference_hardware(
        {
            "performance_budget": {
                "reference_hardware": {"cpu": "OWNER_LOCKED", "ram_gb": 64}
            }
        }
    )
    assert overridden["cpu"] == "OWNER_LOCKED"
    assert overridden["ram_gb"] == 64
    assert overridden["os"] == auto["os"], "trường owner để trống vẫn được tự dò"


def test_four_level_codec_agrees_across_quantum_and_risk_packages() -> None:
    """P1-7: mapping bit→% được cài ĐỘC LẬP hai lần, không share code.

    - `qshield_quantum.formulation.four_level.decode_action_levels` -> phần trăm (10, 20, 30)
    - `qshield_risk.sampling.decode_four_level_bits`                -> phân số (0.10, 0.20, 0.30)

    Hiện hai bên khớp nhau, nhưng không có gì bắt được nếu ai đó sửa một bên (VD đổi grid hành
    động, hay đổi bit order). Lệch nhau ở đây là bug IM LẶNG tệ nhất trong repo: Risk sẽ lấy mẫu
    objective cho một hành động, Quantum decode bitstring thắng cuộc thành một hành động KHÁC, và
    mọi con số vẫn trông hợp lệ. Duyệt hết 4^3 = 64 tổ hợp để khoá lại.
    """
    import itertools

    from qshield_risk.sampling import decode_four_level_bits

    candidate_count = 3
    for bits in itertools.product((0, 1), repeat=2 * candidate_count):
        vector = np.asarray(bits, dtype=np.int8)
        quantum_pct = decode_action_levels(vector)
        risk_fraction = decode_four_level_bits(vector, candidate_count=candidate_count)
        np.testing.assert_allclose(
            np.asarray(quantum_pct, dtype=float) / 100.0,
            risk_fraction,
            atol=1e-12,
            err_msg=f"codec lệch tại bits={bits}",
        )

    # Và cả hai phải khớp đúng bảng mapping trong profile, không chỉ khớp lẫn nhau.
    expected = {"00": 0, "10": 10, "01": 20, "11": 30}
    for pair, percent in expected.items():
        vector = np.asarray([int(pair[0]), int(pair[1])], dtype=np.int8)
        assert int(decode_action_levels(vector)[0]) == percent
        # `pytest.approx`, KHÔNG so bằng chính xác: phía risk cộng 0.10 + 0.20 nên mức 30% ra
        # 0.30000000000000004. Đây là artifact số thực có thật, `rerank.polish_reductions` đã
        # phải chuẩn hoá riêng cho nó (xem comment ở rerank.py) — test không được giả vờ nó
        # không tồn tại, cũng không được coi nó là lỗi codec.
        assert float(
            decode_four_level_bits(vector, candidate_count=1)[0]
        ) == pytest.approx(percent / 100.0)
