# Hiện thực `packages/quantum` + `packages/pipeline` — 2026-08-06

Trước phiên này, cả hai package chỉ là scaffold (`raise NotImplementedError`, xem
`docs/perf/2026-08-04-pipeline-timing.md` §"Chặng chưa hiện thực"). Phiên này hiện thực đầy đủ cả
hai theo `plan.md` (đã viết lại theo đúng phạm vi khóa của CLAUDE.md: 8 mã, QUBO 8-bit, chọn đúng
K=3, công thức closed-form từ `g`/`C`/`c` — không phải scope PSS/PRS cũ).

**Kết luận ngắn:** `packages/quantum` chạy được đầy đủ ở chế độ `--mock` (verify/exact/QAOA/
benchmark), test 40/40 pass. `packages/pipeline` orchestrate được 5 bước nhưng dừng đúng ở chặng
`risk` vì `packages/risk` vẫn là scaffold — đúng như acceptance test đã đề ra. Trong lúc verify end-
to-end thật (không chỉ unit test), phát hiện và sửa **2 bug môi trường nghiêm trọng** không liên
quan tới logic tài chính (xem §3).

## 1. `packages/quantum` — đã hiện thực

| File | Nội dung |
|---|---|
| `formulation/objective.py` | Ground truth: `f(z) = −g'z + λ₁·z'Cz + λ₂·c'z + P·(Σz−K)²` (CLAUDE.md quy tắc 14) |
| `formulation/penalty.py` | `penalty_terms()` + `suggest_penalty()` (không hard-code P) |
| `formulation/qubo.py` | Gộp `λ₁·C` + penalty terms thành QUBO đầy đủ |
| `formulation/qiskit_program.py` | Convert sang `QuadraticProgram` — đã tự verify quy ước hệ số qiskit (áp dụng đúng 1 lần, không nhân đôi như ma trận đối xứng đầy đủ) |
| `verify/consistency.py` | Đối chiếu NumPy / `QuadraticProgram` / QUBO trên toàn bộ 256 bitstring (quy tắc 15) |
| `solvers/exact.py` | Duyệt hết 2⁸=256 trạng thái — thước đo, không phải đối thủ (quy tắc 16) |
| `solvers/qaoa.py` | QAOA p=1, `StatevectorSampler`, COBYLA, ≥10 seed bắt buộc, không cherry-pick (quy tắc 18) |
| `benchmark.py` | So sánh exact / QAOA / classical (greedy theo `g`) — báo cáo trung thực kể cả khi QAOA thua (quy tắc 18) |
| `decode.py` | Bitstring → hành động → tỷ trọng mới (validate tổng = 1.0) |
| `io.py` / `fixtures.py` | Đọc `action_effects.csv`/`pairwise_effects.csv` thật, hoặc sinh giả cho `--mock` |
| `cli.py` | `qshield-quantum solve` — verify → exact → QAOA → benchmark → `qaoa_result.json` |

**Test:** `packages/quantum/tests/` — 40 test (gộp cả `packages/pipeline`), pass sạch, exit code
đúng, có test riêng buộc `verify_consistency` phải FAIL rõ ràng khi cố tình làm lệch công thức.

**Blocker đã biết (ghi trong code, không né tránh):** chấm lại bằng true CVaR (quy tắc 17) —
`qshield_risk.evaluate()` chưa tồn tại → `cli.py` raise `NotImplementedError` khi chạy không
`--mock`; ở `--mock`, `true_cvar_before/after = NaN` kèm `logger.warning`, không được dùng làm bằng
chứng baseline.

## 2. `packages/pipeline` — đã hiện thực

| File | Nội dung |
|---|---|
| `run_context.py` | `PipelineRunContext` — sinh 1 `run_id` dùng chung cho cả 5 bước (mode `runs`), tiêm vào config qua file tạm |
| `stages.py` | Thứ tự 5 bước: data → regime → scenarios → risk → optimize |
| `run.py` | Chạy tuần tự, fail-fast đúng chặng, bọc lỗi thành `StageError` |
| `cli.py` | `qshield-pipeline all` (có `@app.callback()` — tránh bug Typer đã đo ở §5 của doc 2026-08-04) |

**Acceptance test (khớp `plan.md`):** chạy tới đúng chặng `risk` (chưa implement) rồi dừng rõ
ràng, không chạy tiếp `optimize` — verify bằng test tự động
(`packages/pipeline/tests/test_run.py::test_run_all_reaches_risk_stage_and_stops_there`) và bằng
tay qua CLI thật.

## 3. Hai bug môi trường phát hiện khi verify thật (không phải suy đoán)

### 3.1. qiskit + pyarrow segfault khi cùng một tiến trình

Thiết kế ban đầu ở `plan.md` (câu hỏi 6) định cho `run.py` **import trực tiếp** hàm CLI của từng
package (nhanh hơn subprocess). Khi thử chạy thật, phát hiện: nếu `qshield_quantum` (qiskit + Rust
`_accelerate.abi3.so`) và `qshield_ai`/`qshield_data` (ghi `.parquet` qua pyarrow) cùng sống trong
MỘT tiến trình Python, lệnh ghi parquet **sau đó** sẽ segfault (exit code 139) bên trong bộ cấp
phát mimalloc của pyarrow — bất kể thứ tự import. Tái hiện 100% bằng:

```bash
uv run python -X faulthandler -c "
import qshield_quantum.cli
import qshield_ai.cli as ai_cli
ai_cli.regime(config='...', mock=True)"
# → Fatal Python error: Segmentation fault
#   File pandas/io/parquet.py, line 229 in write
#   File pyarrow/parquet/core.py, line 2055 in write_table
```

**Fix:** đổi `run.py` sang chạy MỖI chặng trong MỘT tiến trình con riêng (subprocess:
`python -c "from <module>.cli import app; app()" <subcommand> --config ...`) — mỗi tiến trình con
chỉ import đúng một package nặng, không bao giờ có qiskit và pyarrow-write cùng lúc. Đây là quyết
định bắt buộc về tính đúng đắn, không phải tối ưu tốc độ.

### 3.2. `uv run pytest` (lệnh CLAUDE.md công bố) lỗi trên toàn repo

Mọi package trong workspace (`contracts`, `data`, `ai`, `risk`, `quantum`, `pipeline`) đều có
`tests/__init__.py` riêng nhưng **cùng tên package `"tests"`**. Với import-mode mặc định của
pytest (`prepend`), mọi test module bị nạp vào chung một khóa `sys.modules["tests"]` — package đầu
tiên được collect "thắng", các package sau lỗi `ModuleNotFoundError: No module named
'tests.test_xxx'`. Bug này tồn tại từ trước, không phải do phiên này gây ra — verify bằng cách
chạy `uv run pytest packages/ai packages/data packages/contracts packages/risk` (không đụng
`quantum`/`pipeline`) vẫn lỗi y hệt.

**Fix:** thêm `addopts = ["--import-mode=importlib"]` vào `[tool.pytest.ini_options]` ở
`pyproject.toml` gốc — import theo đường dẫn file thật, không dùng chung `sys.modules["tests"]`.
Đây là cách pytest chính thức khuyến nghị cho đúng tình huống monorepo nhiều thư mục `tests/` trùng
tên.

### 3.3. Bug phụ đã sửa trong lúc verify (không đổi hành vi mặc định)

- `_resolve_run_id()` của `qshield_ai`/`qshield_quantum` (`cli.py`): thêm nhánh đọc khóa `run_id`
  từ config nếu có (do `packages/pipeline` tiêm vào) — trước đây mỗi CLI con tự sinh `run_id`
  riêng, khiến một lần chạy pipeline ở mode `runs` bị chia thành nhiều `run_id` khác nhau (bug đã
  đo ở `docs/perf/2026-08-04-pipeline-timing.md` §6).
- `packages/quantum/tests/conftest.py`: `pytest_sessionfinish` gọi `os._exit()` quá sớm (trước khi
  `TerminalReporter` in dòng tổng kết "N passed in Xs") làm mất dòng đó khi output bị pipe — chuyển
  sang hook `pytest_unconfigure` (chạy sau cùng) + flush thủ công stdio.

## 4. Trạng thái hiện tại

```
uv run pytest packages/quantum packages/pipeline -q
# 40 passed in ~10s, exit code 0
```

`uv run qshield-pipeline all --config configs/base.yaml` (không `--mock`) sẽ chạy `data` →
`regime` → `scenarios` thành công trên dữ liệu thật hiện có, rồi dừng rõ ràng tại `risk` với thông
báo `Chặng 'Risk (qshield-risk effects)' thất bại: ...`. Đây là hành vi ĐÚNG như thiết kế, không
phải lỗi — `packages/risk` là blocker duy nhất còn lại trước khi có thể chạy full pipeline và có
`benchmark.json`/CVaR thật.

## 5. Việc còn lại

1. `packages/risk` hiện thực thật (CVaR trước/sau, `g`/`C`/`c`, `evaluate()`) — mở khóa cả
   `packages/quantum` (true CVaR re-score, quy tắc 17) lẫn full pipeline.
2. Sau khi có `packages/risk`, chạy `qshield-quantum solve` trên dữ liệu thật → benchmark thật đầu
   tiên (`artifacts/dev/optimization/benchmark.json`) — hiện tại benchmark mới chỉ chạy trên
   `--mock`/fixtures trong test, chưa có số thật nào để báo cáo.
3. Xóa `packages/quantum/src/qshield_quantum/fixtures.py` khi `packages/risk` thay thế hoàn toàn
   (đã ghi rõ trong docstring file đó là TEMPORARY).
