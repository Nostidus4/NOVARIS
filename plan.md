# Plan — chạy full `packages/quantum` + `packages/pipeline` trên dữ liệu thật + 2 notebook

Ghi chú: thay nội dung `plan.md` trước (risk candidate selection — đã xong, đã chạy thật, xem báo
cáo cuối phiên trước). Đây là plan cho task tiếp theo.

---

## 0. Bối cảnh — vì sao đây là lúc làm được "full"

Ba việc trước đó đã mở khóa đúng những gì "full" cần:

1. `packages/risk` hóa ra đã hiện thực đầy đủ (không phải scaffold) — `action_effects.csv`,
   `pairwise_effects.csv`, `baseline_risk.json` giờ có bản THẬT trong `artifacts/dev/risk/`.
2. `qshield_risk.evaluate()` — hàm chấm true CVaR — cũng đã có sẵn (phát hiện ở plan trước, chưa
   dùng tới).
3. Đã có 3 notebook chạy thật, tuần tự: `data_exploration.ipynb` → `ai_regime_scenarios.ipynb` →
   `risk_effects.ipynb`. Artifact thật cho tới hết chặng Risk đã tồn tại trên đĩa.

**Việc còn thiếu duy nhất để "full" thật sự đúng nghĩa:** `packages/quantum/cli.py::solve()` khi
KHÔNG `--mock` đang cố ý `raise NotImplementedError` ở đúng bước chấm true CVaR (CLAUDE.md quy tắc
17) — với comment "BLOCKED tới khi packages/risk có thật". Giờ đã hết blocked. Đây là việc code
thật cần làm trước khi có thể viết notebook (không thể "notebook hoá" một lệnh còn cố ý crash).

**Benchmark thật:** đúng như đã nói ở phiên trước — `benchmark.json` (so sánh exact/QAOA/classical)
tới giờ mới chỉ chạy trên `--mock`/fixtures trong test. Chạy `solve` thật (không mock) lần đầu tiên
sẽ tự động tạo ra `benchmark.json` **thật đầu tiên** — đúng phần "benchmark đã đề cập" bạn nhắc.

---

## 1. Sửa `packages/quantum/src/qshield_quantum/cli.py`

### 1.1. Đọc `baseline_risk.json` thật (hiện đang hard-code `None`)

```python
baseline = None  # TODO: đọc baseline_risk.json thật khi packages/risk có (plan.md §1)
```

→ đổi thành đọc thật, kiểm tra tồn tại giống 2 file kia (thêm `baseline_risk.json` vào danh sách
file bắt buộc phải có trước khi chạy không-mock).

### 1.2. Chấm true CVaR bằng `qshield_risk.evaluate()` (thay khối `raise NotImplementedError`)

`evaluate(bitstring, scenarios, ticker_order, weights, cash_weight, config)` cần **scenario cube
thật** (không chỉ `baseline_risk.json`) — viết thêm `_load_scenario_cube()` cục bộ trong
`quantum/cli.py` (đọc lại `artifacts/dev/scenarios/{stress_scenarios.npz,scenario_manifest.json}`,
validate `gate_status=PASS` + đúng `ticker_order` — độc lập với validate của `packages/risk`, đúng
CLAUDE.md quy tắc 12 "validate ở mọi ranh giới module", không tin ngầm dữ liệu chặng trước).

`config` truyền vào `evaluate()` chính là `cfg` đã có sẵn trong `solve()` — `Config.load()` gộp
phẳng toàn bộ include (`risk.yaml` nằm trong `configs/base.yaml`), nên `cfg` đã có sẵn
`action_reduction_pct`, `transaction_cost`, `weight_sum_tolerance`, `k_actions` mà `evaluate()`
cần, không phải truyền config riêng.

```python
bits = [int(b) for b in winning_bitstring]
risk_eval = qshield_risk.evaluate.evaluate(
    bits, scenario_cube, tickers,
    weights=baseline["portfolio_weights"], cash_weight=float(baseline["cash_weight"]), config=cfg,
)
primary_key = qshield_risk.metrics.alpha_key(alpha)
true_cvar_before = risk_eval.before.cvar[primary_key]
true_cvar_after = risk_eval.after.cvar[primary_key]
```

Cross-import `qshield_risk` từ `qshield_quantum` — **đã được khai báo sẵn** trong
`packages/quantum/pyproject.toml` (`qshield-risk` nằm trong `dependencies`) và **đúng** CLAUDE.md
quy tắc 11 (chiều phụ thuộc một chiều: `risk ← quantum`, tức quantum được phép import risk cho
đúng việc chấm true CVaR — cross-import DUY NHẤT được phép trong toàn repo).

Log rõ nếu nghiệm KHÔNG cải thiện true CVaR (`risk_eval.improves_primary_cvar is False`) — trung
thực theo quy tắc 18, không diễn giải có lợi.

### 1.3. Vẫn cần `transaction_cost`/`weight_sum_tolerance` (TBD-002)

`evaluate()` gọi `CostRates.from_config(cfg)` y hệt `packages/risk` — nghĩa là `qshield-quantum
solve` (không mock) **cũng cần config PROVISIONAL** giống notebook Risk trước (đã được bạn đồng ý
dùng placeholder). Notebook quantum sẽ tự dựng resolved config, KHÔNG sửa `configs/risk.yaml` gốc
— giữ nguyên convention đã lập.

### 1.4. Cập nhật docstring đầu file

Bỏ câu "BLOCKED tới khi packages/risk có thật" — không còn đúng.

---

## 2. Test mới cho `packages/quantum`

Thêm vào `packages/quantum/tests/test_cli.py`, đánh dấu `@pytest.mark.slow` + cô lập subprocess
(đúng pattern đã có, tránh bẫy qiskit/pyarrow đã verify): dựng fixture 4-mã nhỏ gồm đủ
`baseline_risk.json` + `action_effects.csv` + `pairwise_effects.csv` (tay, không cần chạy risk
thật) + `scenario_manifest.json`/`stress_scenarios.npz` (tay, cube ngẫu nhiên nhỏ), chạy `solve`
không `--mock`, assert `true_cvar_before`/`true_cvar_after` là số thật (không NaN) và
`validate_qaoa_result` pass. Test cũ (`test_solve_without_mock_and_without_risk_fails_clearly`)
không đổi — vẫn đúng vì nó test path "chưa có risk artifact nào", không đụng logic mới.

---

## 3. Notebook 1: `notebooks/exploration/quantum_solve.ipynb`

**⚠️ Khác 3 notebook trước ở một điểm quan trọng — PHẢI chạy qua subprocess, không import trực
tiếp:**

1. **Bẫy qiskit+pyarrow đã verify** (`docs/perf/2026-08-06-quantum-pipeline-implementation.md`
   §3.1): import `qshield_quantum` (qiskit) rồi ghi `.parquet` (pyarrow) trong CÙNG một tiến trình
   sẽ segfault.
2. **Bẫy mới, riêng cho notebook (chưa từng gặp ở 3 notebook trước vì chúng không đụng quantum):**
   `qshield_quantum.cli.solve()` tự gọi `os._exit(0)` ở cuối khi chạy standalone (né hang
   `Py_FinalizeEx` của qiskit — xem `_fast_exit_if_standalone()`). Gọi hàm này TRỰC TIẾP trong
   kernel Jupyter (không phải subprocess, không phải pytest) sẽ **giết luôn kernel** ngay khi
   `solve()` chạy xong — mất hết state, mất luôn khả năng chạy cell tiếp theo.

→ Notebook gọi `qshield-quantum solve` qua `subprocess.run([sys.executable, "-c", "from
qshield_quantum.cli import app; app()", "solve", "--config", ..., ...])` — đúng pattern
`packages/pipeline/run.py`/test suite của quantum đã dùng — rồi đọc lại file JSON kết quả từ đĩa để
hiển thị. Không có cách nào khác an toàn.

Nội dung:
1. Kiểm tra tiên quyết: `artifacts/dev/risk/{baseline_risk.json,action_effects.csv,
   pairwise_effects.csv}` đã có (từ `risk_effects.ipynb`).
2. Dựng resolved config: PROVISIONAL `transaction_cost`/`weight_sum_tolerance` (giống hệt
   `risk_effects.ipynb`, dùng lại đúng số đó cho nhất quán).
3. Chạy `qshield-quantum solve --config <resolved>` qua subprocess (không `--mock`).
4. Đọc + hiện `qaoa_result.json` (bitstring, `true_cvar_before`/`after`, `optimality_gap`,
   `feasibility_rate`, `actual_solver`).
5. Đọc + hiện `benchmark.json` — **benchmark thật đầu tiên** (exact vs QAOA vs classical,
   `qaoa_beats_classical`). Không diễn giải có lợi nếu QAOA thua (quy tắc 18) — in nguyên trạng.
6. Tổng thời gian chạy (1 số, đúng yêu cầu trước đó).

---

## 4. Notebook 2: `notebooks/exploration/pipeline_full_run.ipynb`

`qshield_pipeline.run.run_all()` **an toàn gọi trực tiếp trong notebook** — bản thân nó đã tự cô
lập từng chặng bằng subprocess (đúng thiết kế đã verify), nên tiến trình notebook không bao giờ
import trực tiếp `qshield_quantum`. Không cần trick subprocess-of-subprocess.

Đây sẽ là lần đầu tiên `qshield-pipeline all` chạy thật, không mock, đủ 5 chặng — trước giờ test
của `packages/pipeline` toàn monkeypatch `_run_stage_subprocess`, chưa từng chạy thật end-to-end.

Nội dung:
1. Dựng resolved config: base config + PROVISIONAL risk override (giống notebook 1), ghi ra file
   tạm.
2. Gọi `qshield_pipeline.run.run_all(resolved_config_path, mock=False)`.
3. Lưu ý thời gian: chặng `data` sẽ **fetch lại thật** qua mạng (đã verify chạy được trong môi
   trường này, nhưng mất thời gian hơn 4 chặng còn lại cộng lại).
4. Bắt `StageError` nếu có chặng lỗi — in rõ chặng nào, không nuốt lỗi.
5. Hiện checklist toàn bộ artifact 5 chặng + tổng thời gian.

---

## 5. Thứ tự thực hiện

1. Sửa `packages/quantum/cli.py` (§1) + test mới (§2), chạy `pytest packages/quantum` xác nhận
   xanh.
2. Viết + chạy thử thật `quantum_solve.ipynb` (§3) — xác nhận `benchmark.json` thật ra số hợp lý,
   `true_cvar_before/after` không NaN.
3. Viết + chạy thử thật `pipeline_full_run.ipynb` (§4) — xác nhận `qshield-pipeline all` thật chạy
   hết 5 chặng không lỗi.
4. `ruff check`/`ruff format` toàn bộ, `pytest` toàn bộ package đã đụng.

## 6. Việc KHÔNG làm trong plan này

- Không đổi `configs/risk.yaml` thành số thật (vẫn PROVISIONAL qua resolved-config, như đã thống
  nhất).
- Không sửa `packages/pipeline/run.py` để gọi thêm `qshield-risk candidates` (bước top-10) — ở
  scope 8 mã hiện tại không ảnh hưởng kết quả quantum (không lọc gì), để dành khi có 30 mã thật.
- Không động tới `packages/quantum/formulation/` cho 20-bit/`workflow_update` — vẫn đúng scope
  `demo_fast` (8-bit, K=3) như hiện tại.

## 7. Không có câu hỏi chặn — có thể bắt đầu ngay sau khi bạn duyệt plan này

(Khác 2 plan trước — không còn quyết định tài chính/thiết kế mới nào cần hỏi, mọi thứ dùng lại
đúng quyết định đã có: PROVISIONAL transaction cost, N≤10 không lọc, scope demo_fast.)
