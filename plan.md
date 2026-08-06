# Plan implement `packages/quantum/` + `packages/pipeline/`

**Mục tiêu:** biến `packages/quantum/` và `packages/pipeline/` từ scaffold (mọi file 1 dòng comment,
CLI raise `NotImplementedError`) thành package thật, đúng **phạm vi đã khóa** trong CLAUDE.md và
`docs/limitations.md` §1 — không phải thiết kế PSS/PRS gốc.

---

## 0. CẢNH BÁO PHẠM VI — đọc trước khi viết bất kỳ dòng nào

Bản `plan.md` trước đây (đã bị ghi đè bởi file này) viết trực tiếp từ
`docs/product/product_requirements.md`/`acceptance_criteria.md`/`mvp_scope.md` — tức **thiết kế đầy
đủ gốc (PSS/PRS)**, chưa đối chiếu với CLAUDE.md/`docs/Structure.md`/source code thật. Đây đúng loại
lỗi mà `docs/limitations.md` §1 cảnh báo: *"Khi đọc bất kỳ số liệu nào từ hệ thống, phải hiểu đó là
kết quả trên phạm vi đã khóa, không phải trên thiết kế 30-mã/top-10/20-bit"*. `packages/ai` đã từng
dính đúng nhầm lẫn này và phải viết `docs/architecture/ai-decisions-v0.2.md` để tách lại — plan này
tách ngay từ đầu, đỡ phải sửa sau.

| Thông số | Thiết kế gốc (PSS/PRS — **KHÔNG làm**) | Phạm vi đã khóa (CLAUDE.md — **làm cái này**) |
|---|---|---|
| Universe / ứng viên | 30 mã VN30, top 10 chọn động | 8 mã (`configs/universe.yaml`), cả 8 đều là ứng viên |
| Số bit QUBO | 20 bit (2 bit/mã, 4 mức hành động) | **8 bit** (1 bit/mã — chọn hay không chọn) |
| Mức hành động | 0% / 10% / 20% / 30% | Một mức duy nhất: **giảm 20% vị thế** |
| Cách dựng QUBO | Fit surrogate bậc 2 từ 211+ mẫu objective (Möbius) qua Risk Engine | **Closed-form trực tiếp** từ `g`, `C`, `c` đã có sẵn (không sampling, không fit) |
| Solver chính | Warm-start QAOA p=1 bắt buộc, p=2 challenger | QAOA `p=1` — warm-start **chưa xác định bắt buộc hay không** (xem câu hỏi 2) |
| Local polishing | Có, ±5 điểm % | **Không có** trong phạm vi đã khóa |
| Candidate pool consolidation (exact+QAOA+classical) | Có | Không — báo cáo riêng từng solver theo đúng `QaoaResult` (đã có schema thật) |
| Dashboard | Streamlit độc lập | Next.js (`frontend/`) gọi qua `backend/` FastAPI — không thuộc `packages/quantum` |
| Stack | Python 3.11, `pip-tools`, cấu trúc `qshield/` riêng | Python 3.14, `uv` workspace, `packages/quantum/`, `packages/pipeline/` (đã có sẵn) |
| Exact solver | Duyệt 2²⁰ = 1.048.576 trạng thái | Duyệt 2⁸ = **256** trạng thái (CLAUDE.md quy tắc 16) |

Mọi mục còn lại của plan này **chỉ bám phạm vi đã khóa**. `docs/product/*.md` chỉ dùng để hiểu ngữ
cảnh/lý do thiết kế (vd vì sao có exact solver, vì sao có benchmark), không phải spec để implement.

---

## 1. Blocker lớn nhất: `packages/risk/` chưa hề implement

`packages/risk/` hiện chỉ có **34 dòng tổng cộng** (toàn scaffold 1 dòng comment) — xác nhận lại tại
thời điểm viết plan này, khớp với `docs/perf/2026-08-04-pipeline-timing.md` ("3 trong 6 chặng chưa
hiện thực"). Hệ quả trực tiếp cho `packages/quantum`:

- Không có `action_effects.csv`/`pairwise_effects.csv`/`baseline_risk.json` thật → không có `g`,
  `C`, `c` thật để dựng QUBO.
- Rule 17 (CLAUDE.md): *"Nghiệm QAOA phải chấm lại bằng true CVaR qua `qshield_risk.evaluate`"* —
  đây là **import chéo DUY NHẤT được phép** (`risk ← quantum`) và nó trỏ vào một hàm chưa tồn tại.

**Cách xử lý đề xuất — theo đúng pattern đã có tiền lệ trong repo** (`packages/ai/src/qshield_ai/
fixtures.py`, do Tú viết khi `qshield_contracts.mocks` chưa có, tự xóa khi hết cần):

Viết `packages/quantum/src/qshield_quantum/fixtures.py` — **TẠM THỜI**, sinh `g`/`C`/`c`/
`baseline_risk` giả nhưng đúng `schemas/risk.py` (đã có thật trong `packages/contracts`), đủ để
`packages/quantum` build/test/chạy độc lập qua `--mock`. Khi `packages/risk` có thật, xóa file này,
đổi `cli.py` sang đọc artifact thật — không giữ hai nguồn song song.

Đây là quyết định khác với `packages/data` (nơi ta đã bỏ hẳn mock vì luôn có dữ liệu thật để chạy) —
ở đây **không có lựa chọn nào khác** vì risk thật không tồn tại, không phải vì "cho nhẹ". Xem câu
hỏi 1 ở §8 nếu có người khác đang làm `packages/risk` song song — plan này giả định chưa ai làm.

---

## 2. Ràng buộc CLAUDE.md áp dụng trực tiếp cho quantum (trích lại để bám sát khi code)

14. `formulation/objective.py` là ground truth: `f(z) = -g'z + λ₁·z'Cz + λ₂·c'z + P·(Σz − K)²`.
15. Chạy `verify/consistency.py` **trước khi tin bất kỳ kết quả QAOA nào**.
16. Exact solver duyệt đủ 256 bitstring — không bỏ để tiết kiệm thời gian.
17. Nghiệm QAOA phải chấm lại bằng true CVaR qua `qshield_risk.evaluate`, không phải objective value.
18. Không tuyên bố quantum advantage — QAOA thua exact/classical thì báo cáo trung thực.

Cộng thêm quy tắc chung: quy ước dấu `L = -R` (1), tổng tỷ trọng luôn = 1.0 kể cả tiền mặt (6),
không hard-code (8), backend/frontend không chứa công thức tài chính (9-10), validate ở mọi ranh
giới (12), chỉ `RunContext` ghi metadata (13).

---

## 3. Bảng mapping file — `packages/quantum/`

| File | Việc cần làm | Đối chiếu được thực tế? |
|---|---|---|
| `formulation/objective.py` | Hàm NumPy thuần `f(z)` — ground truth, xem §6.1 | Không — chưa có `g/C/c` thật, dùng fixtures |
| `formulation/qubo.py` | Dựng ma trận `Q` (8×8) + vector tuyến tính từ `g/C/c` — phải cho energy khớp `objective.py` tuyệt đối | — |
| `formulation/penalty.py` | Khai triển `P·(Σz−K)²` thành QUBO terms — hàm riêng vì `qubo.py` và `qiskit_program.py` cùng dùng | — |
| `formulation/qiskit_program.py` | `QuadraticProgram` (qiskit_optimization) từ `g/C/c` → `QuadraticProgramToQubo` | — |
| `verify/consistency.py` | So 3 cách tính trên **toàn bộ 256 bitstring** (không phải mẫu) — cổng chặn bắt buộc | — |
| `solvers/exact.py` | Duyệt 256 bitstring bằng `objective.py`, tìm min trong tập feasible (Σz=K) | — |
| `solvers/qaoa.py` | qiskit 2.x: `StatevectorSampler` + `qiskit_algorithms.QAOA` + `COBYLA` + `MinimumEigenOptimizer`, ≥10 seed, p=1 | — |
| `solvers/warm_start.py` | **Tùy chọn theo Structure.md** — xem câu hỏi 2 trước khi viết | — |
| `backends/simulator.py` | Wrap `StatevectorSampler(default_shots=1024, seed=...)` | — |
| `backends/hardware.py` | ĐỂ TRỐNG — không đụng | — |
| `decode.py` | bitstring (8 bit, thứ tự = `configs/universe.yaml`) → action_id → ticker → tỷ trọng mới (giảm 20%, phần dư → tiền mặt) | — |
| `benchmark.py` | gap, feasibility_rate, success_prob, runtime, circuit depth + 1 classical baseline (câu hỏi 5) | — |
| `fixtures.py` ⚠️ **file mới, tạm thời** | Sinh `g/C/c/baseline_risk` giả đúng `schemas/risk.py`, xóa khi `packages/risk` có thật | Có — đối chiếu `schemas/risk.py` đã implement |
| `cli.py` | `qshield-quantum solve` — orchestrate toàn bộ, xem §6.8 | — |

---

## 4. Bảng mapping file — `packages/pipeline/`

| File | Việc cần làm |
|---|---|
| `stages.py` | Định nghĩa thứ tự chạy: `data → regime → scenarios → risk → optimize`. QUBO+Solve gộp thành **một** lời gọi `qshield-quantum solve` (khớp `ArtifactPaths`: `Stage.QUBO`/`Stage.SOLVE` đã dùng chung thư mục `optimization/`, xem `packages/contracts/paths.py`) |
| `run_context.py` | Wrap `qshield_contracts.paths.ArtifactPaths` + `qshield_contracts.runs.RunContext`, sinh **một** `run_id` dùng chung cho toàn bộ pipeline — xem §5 (fix bug run_id đã biết) |
| `run.py` | Chạy tuần tự từng chặng, `validate_or_raise` giữa mỗi chặng, fail-fast có ngữ cảnh (chặng nào, lỗi gì), ghi `metrics.json` tổng hợp qua `RunContext` |
| `cli.py` | `qshield-pipeline all` — gọi `run.py`, thêm `@app.callback()` rỗng (fix bug đã biết, xem §5) |

---

## 5. Nợ kỹ thuật đã biết cần xử lý trong phạm vi package này

Từ `docs/perf/2026-08-04-pipeline-timing.md` (đo thật, không suy đoán):

1. **§5 — `qshield-pipeline` chạy `all` báo lỗi "unexpected extra argument".** Typer tự đưa command
   duy nhất lên thành root command. Fix: thêm `@app.callback()` rỗng trong `pipeline/cli.py` (đã có
   tiền lệ đúng ở `qshield_ai/cli.py::_main`, copy cách làm).
2. **§6 — `artifacts.mode: runs` không dùng chung `run_id` giữa các chặng.** Mỗi CLI con (`qshield-
   ai regime`, `qshield-ai scenarios`, ...) tự sinh `run_id` riêng theo timestamp khi gọi độc lập →
   chặng sau không thấy artifact chặng trước. Đây **chính là việc của `packages/pipeline/
   run_context.py`**: sinh `run_id` một lần, phải truyền được xuống từng chặng. Xem câu hỏi 6 — cách
   truyền quyết định `run.py` gọi từng package kiểu gì (import hàm hay subprocess CLI).
3. **§8 — `qshield-data` crash `UnicodeEncodeError` trên console không phải UTF-8** khi gọi trước
   `@app.callback()` chạy (vd `--help`). Đây là bug của `packages/data` (không phải phạm vi plan
   này), nhưng `packages/pipeline/cli.py` cần tự có `_tolerate_legacy_console_encoding()` riêng
   (copy từ `qshield_ai/cli.py`) để `qshield-pipeline --help` không dính lỗi tương tự.

Không thuộc phạm vi package này nhưng ảnh hưởng runtime pipeline: `qshield-data split` vẫn còn chậm
(~62s, `.apply()` per-row parse ngày lặp lại — xem perf doc §4) — chưa được `packages/data` sửa tại
thời điểm viết plan này. Không tự sửa ở đây (khác owner/package), chỉ lưu ý khi đo runtime pipeline.

---

## 6. Interface chi tiết

### 6.1. `formulation/objective.py`

```python
import numpy as np

def objective(
    z: np.ndarray,        # (8,) — 0/1, thứ tự = configs/universe.yaml
    g: np.ndarray,         # (8,) — CVaR_0 - CVaR_i mỗi hành động, từ ActionEffectsSchema
    C: np.ndarray,          # (8,8) — ma trận tương tác cặp, từ PairwiseEffectsSchema (đối xứng)
    c: np.ndarray,           # (8,) — chi phí giao dịch, từ ActionEffectsSchema
    lambda_1: float,
    lambda_2: float,
    penalty: float,
    k_actions: int,
) -> float:
    """f(z) = -g'z + lambda_1 * z'Cz + lambda_2 * c'z + penalty * (sum(z) - K)^2.

    GROUND TRUTH — formulation/qubo.py và formulation/qiskit_program.py phải cho energy khớp
    hàm này tuyệt đối trên toàn bộ 256 bitstring (verify/consistency.py kiểm tra việc đó).
    """
```

### 6.2. `formulation/qubo.py` + `formulation/penalty.py`

```python
# penalty.py
def penalty_terms(n: int, k_actions: int, penalty: float) -> tuple[np.ndarray, np.ndarray, float]:
    """Khai triển P*(sum(z)-K)^2 = P*sum(z_i^2) + 2P*sum_{i<j}(z_i z_j) - 2PK*sum(z_i) + P*K^2.
    z_i^2 = z_i (nhị phân) nên gộp vào phần tuyến tính. Trả (Q_add (n,n), linear_add (n,), const_add)."""


# qubo.py
def build_qubo(
    g: np.ndarray, C: np.ndarray, c: np.ndarray, *,
    lambda_1: float, lambda_2: float, penalty: float, k_actions: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Trả (Q, linear, constant) sao cho z'Qz + linear'z + constant == objective.objective(z, ...)
    với mọi z — test bằng cách so trên toàn bộ 256 bitstring, không chỉ vài mẫu."""
```

### 6.3. `formulation/qiskit_program.py`

```python
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo

def build_quadratic_program(g, C, c, *, lambda_1, lambda_2, penalty, k_actions) -> QuadraticProgram:
    """8 biến nhị phân z_0..z_7 (đặt tên theo ticker), objective = objective.py, KHÔNG thêm
    constraint sum(z)=K dạng cứng — pattern đã khóa là ép qua penalty trong objective, không phải
    qua linear constraint của QuadraticProgram (để giữ đúng 1 QUBO duy nhất mọi solver dùng chung,
    tránh QuadraticProgramToQubo tự thêm penalty riêng gây lệch với formulation/qubo.py)."""
```

### 6.4. `verify/consistency.py`

```python
def verify_consistency(g, C, c, *, lambda_1, lambda_2, penalty, k_actions, atol=1e-9) -> None:
    """So 3 cách tính trên TOÀN BỘ 2**8=256 bitstring (rẻ, không cần mẫu):
    1. objective.objective(z, ...) — NumPy thuần
    2. QuadraticProgram.objective.evaluate(z) (từ qiskit_program.py)
    3. z' Q z + linear'z + constant (từ qubo.py, đã convert qua QuadraticProgramToQubo)
    Raise ValueError liệt kê chính xác bitstring nào lệch bao nhiêu — không chỉ nói "lệch".
    Đây là cổng BẮT BUỘC chạy trước solvers/qaoa.py (CLAUDE.md quy tắc 15).
    """
```

### 6.5. `solvers/exact.py`

```python
@dataclass(frozen=True)
class ExactResult:
    best_bitstring: str          # 8 bit, feasible (sum=K)
    best_energy: float
    all_energies: dict[str, float]  # toàn bộ 256, để benchmark tính percentile/gap


def solve_exact(g, C, c, *, lambda_1, lambda_2, penalty, k_actions) -> ExactResult:
    """Duyệt đủ 2**8=256 bitstring bằng objective.py trực tiếp (KHÔNG qua QUBO convert — đây là
    ground truth độc lập, đúng tinh thần CLAUDE.md quy tắc 16: 'thước đo, không phải đối thủ').
    best_bitstring chọn trong tập FEASIBLE (sum(z)==k_actions) — xem câu hỏi 7 nếu muốn đổi.
    """
```

### 6.6. `solvers/qaoa.py`

Đúng snippet đã verify trong CLAUDE.md/`docs/runbook/troubleshooting.md` §2 — copy y nguyên, không
suy đoán API khác:

```python
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer

def solve_qaoa_one_seed(qubo, *, seed: int, shots: int, maxiter: int) -> dict:
    sampler = StatevectorSampler(default_shots=shots, seed=seed)
    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=1)
    result = MinimumEigenOptimizer(qaoa).solve(qubo)
    # trả bitstring (đã qua to_canonical_bitstring — xem cảnh báo dưới), energy, raw result


def solve_qaoa(qubo, *, seeds: list[int], shots: int, maxiter: int) -> dict[int, dict]:
    """Chạy TOÀN BỘ seed trong danh sách (≥10, không cherry-pick — CLAUDE.md quy tắc 18/rule Q-07
    cũ vẫn đúng tinh thần dù số hiệu khác). Trả {seed: result} đầy đủ, kể cả seed cho kết quả tệ."""
```

⚠️ **Endianness (giữ lại từ plan cũ, vẫn đúng dù đổi 20-bit→8-bit):** Qiskit trả bitstring có thể
đảo thứ tự so với thứ tự biến đã khai báo trong `QuadraticProgram`. Không giả định thứ tự — lấy
mapping biến→bit từ chính `result` (`qiskit_optimization` result đã trả `x` theo đúng thứ tự biến
khai báo, không cần tự đảo tay) và viết 1 test đối chiếu bitstring QAOA với index ticker tương ứng
trong `configs/universe.yaml`.

### 6.7. `benchmark.py`

```python
def build_benchmark(exact: ExactResult, qaoa_by_seed: dict[int, dict], *, k_actions: int) -> dict:
    """optimality_gap = (qaoa_energy - exact.best_energy) / abs(exact.best_energy) mỗi seed.
    feasibility_rate = tỷ lệ shot cho bitstring có sum(z)==k_actions.
    success_prob = xác suất đo được đúng exact.best_bitstring.
    classical_baseline: greedy chọn K mã có g_i lớn nhất (đơn giản nhất có thể biện minh được —
    xem câu hỏi 5), để CLAUDE.md quy tắc 18 ('QAOA thua exact hay thua classical thì báo cáo
    trung thực') có cái để so."""
```

### 6.8. `cli.py` (`qshield-quantum solve`)

```python
@app.command()
def solve(config: str = ..., mock: bool = typer.Option(False, "--mock")) -> None:
    cfg = Config.load(Path(config))
    paths = ArtifactPaths(cfg, run_id=_resolve_run_id(cfg))
    context = RunContext(cfg, paths)

    if mock:
        g, C, c, baseline = fixtures.generate(cfg)  # fixtures.py tạm thời, xem §1
    else:
        g, C, c = registry.load_risk_effects(paths)  # đọc action_effects.csv/pairwise_effects.csv thật
        baseline = registry.load_baseline_risk(paths)

    penalty_cfg = cfg["penalty"]  # lambda_1/lambda_2/P — hiện đang null, xem câu hỏi 3
    verify.verify_consistency(g, C, c, **penalty_cfg, k_actions=cfg["k_actions"])  # BẮT BUỘC trước QAOA

    exact_result = solvers.exact.solve_exact(g, C, c, **penalty_cfg, k_actions=cfg["k_actions"])
    qaoa_results = solvers.qaoa.solve_qaoa(qubo, seeds=cfg["qaoa"]["seeds"], ...)
    bench = benchmark.build_benchmark(exact_result, qaoa_results, k_actions=cfg["k_actions"])

    # CLAUDE.md quy tắc 17 — chấm lại bằng true CVaR, KHÔNG dùng objective value để chọn nghiệm cuối
    if not mock:
        true_cvar_after = qshield_risk.evaluate(winning_bitstring, ...)  # BLOCKED tới khi risk có thật
    else:
        true_cvar_after = None  # --mock không re-rank được, ghi rõ trong manifest

    qaoa_result = QaoaResult(...)  # đúng schemas/optimization.py đã có thật
    validate_or_raise(qaoa_result, ...)
    # ghi qaoa_result.json vào paths.for_stage(Stage.QUBO, "qaoa_result.json")
```

---

## 7. Thứ tự implement (dependency order)

| # | File | Lý do phải xong trước |
|:-:|---|---|
| 1 | `packages/quantum/fixtures.py` | Mọi thứ khác cần `g/C/c` giả để test trong lúc chờ `packages/risk` |
| 2 | `formulation/objective.py` | Ground truth — mọi thứ khác đối chiếu vào đây |
| 3 | `formulation/penalty.py`, `formulation/qubo.py` | Cần `objective.py` để test khớp |
| 4 | `formulation/qiskit_program.py` | Cần `objective.py` để test khớp |
| 5 | `verify/consistency.py` | Cần cả 3 ở trên xong |
| 6 | `solvers/exact.py` | Cần `objective.py`; độc lập với QAOA |
| 7 | `backends/simulator.py`, `solvers/qaoa.py` | Cần `qiskit_program.py` + `verify` đã pass |
| 8 | `decode.py` | Cần `configs/universe.yaml` + kết quả solver |
| 9 | `benchmark.py` | Cần cả exact + qaoa xong |
| 10 | `cli.py` (quantum) | Wire tất cả |
| 11 | `packages/pipeline/run_context.py` | Cần `qshield_contracts.paths`/`runs` (đã có thật) |
| 12 | `packages/pipeline/stages.py`, `run.py` | Cần quantum CLI + risk CLI (chặng risk sẽ fail rõ ràng nếu risk chưa có) |
| 13 | `packages/pipeline/cli.py` | Wire cuối |

**Test nghiệm thu cụ thể:**
- `verify_consistency` pass trên 256/256 bitstring với `g/C/c` từ fixtures.
- `solve_exact` trả đúng bitstring feasible tối ưu, đối chiếu tay trên 1 bộ `g/C/c` nhỏ tự tạo.
- `uv run qshield-quantum solve --config configs/base.yaml --mock` chạy hết, ghi `qaoa_result.json`
  hợp lệ theo `schemas/optimization.py`.
- `uv run qshield-pipeline all --config configs/base.yaml` chạy tới đúng chặng `risk` rồi dừng với
  lỗi rõ ràng ("packages/risk chưa implement"), không crash mơ hồ — vì risk thật sự chưa có.

---

## 8. Câu hỏi cần chốt trước khi code

1. **`packages/risk` — có ai đang làm song song không?** Nếu không, plan này giả định quantum phải
   tự có `fixtures.py` tạm để chạy được (§1). Nếu có người đang làm, nói rõ interface họ sẽ giao
   (`action_effects.csv`/`pairwise_effects.csv`/`baseline_risk.json` — đã có schema thật) để
   `fixtures.py` sinh đúng hình dạng ngay từ đầu.
2. **Warm-start QAOA — bắt buộc hay tùy chọn?** `configs/quantum.yaml` dòng comment ghi *"Warm-start
   QAOA p=1 là cấu hình chính (README.md, mvp_scope.md §11.3)"* — nhưng đó là câu trích từ thiết kế
   PSS gốc (10 candidates/20-bit), còn `docs/Structure.md` liệt kê `solvers/warm_start.py` là *"tùy
   chọn"*. Đề xuất: **bỏ qua warm-start ở lần đầu** (QAOA p=1 thường, không khởi tạo lệch), vì với
   8 qubit bài toán đủ nhỏ để không cần warm-start mới hội tụ. Thêm sau nếu benchmark cho thấy cần.
3. **`λ₁`, `λ₂`, `P` (TBD-006 trong `docs/product/mvp_scope.md` §23) — hiện đang `null`.** Không có
   số nào để chạy thật. Đề xuất: chọn giá trị PROVISIONAL dựa trên độ lớn `g`/`C` thật (P đủ lớn hơn
   `max|g| + max_i sum_j |C_ij|` theo nguyên tắc CLAUDE.md — đủ để penalty luôn thắng), đánh dấu
   `NON_BASELINE_RUN` giống cách `packages/ai` đã làm với `kurtosis_abs_diff_max`. Ai duyệt — Phúc/
   Ngọc theo đúng phân công trong `mvp_scope.md`?
4. **Danh sách 10 seed QAOA cụ thể (`configs/quantum.yaml: qaoa.seeds`, hiện `null`).** Tự chọn tạm
   (vd `0..9`) đánh dấu PROVISIONAL, hay chờ đăng ký chính thức trước?
5. **Classical baseline cho benchmark (CLAUDE.md quy tắc 18 cần "classical" để so).** Chưa có solver
   classical nào trong `docs/Structure.md`. Đề xuất đơn giản nhất: **greedy chọn K mã có `g_i` lớn
   nhất** (bỏ qua tương tác `C`). Đồng ý, hay cần solver mạnh hơn (SA)?
6. **`packages/pipeline/run.py` gọi từng chặng bằng cách nào?**
   - **(a) Import trực tiếp hàm CLI** (`from qshield_data.cli import build`, gọi như hàm Python) —
     nhanh (không tốn ~2-3s khởi động interpreter mỗi lần, khớp phát hiện trong perf doc), nhưng
     **mỗi package con hiện tự sinh `run_id` riêng** khi gọi (`_resolve_run_id` nội bộ) — cần sửa
     nhỏ ở `qshield_data`/`qshield_ai` để nhận `run_id` truyền vào thay vì tự sinh, mới fix được bug
     §5.6 thật sự (không chỉ né nó).
   - **(b) `subprocess.run(["uv", "run", "qshield-data", "build", ...])`** — không cần sửa package
     con, nhưng chậm hơn và **không sửa được bug run_id dùng chung** (mỗi subprocess vẫn tự sinh
     run_id riêng trừ khi truyền qua `--run-id` — cần thêm option đó vào từng CLI con).
   Cả hai đều cần đụng vào package khác (data/ai) ít nhiều. Chọn hướng nào?
7. **`solvers/exact.py` — chỉ tìm min trong tập FEASIBLE (Σz=K), hay trên toàn bộ 256 kể cả
   infeasible (dựa vào penalty tự loại)?** CLAUDE.md quy tắc 16 chỉ nói "duyệt 256 bitstring", không
   nói rõ có lọc feasible trước khi chọn "best" hay không. Đề xuất: báo cáo cả hai — `best_feasible`
   (dùng làm optimum thật) và `best_overall` (để phát hiện penalty quá yếu, bitstring infeasible
   thắng thì `P` chưa đủ lớn — đúng lỗi hay gặp đã ghi trong `docs/runbook/troubleshooting.md` §4).
8. **`verify/consistency.py` — so trên toàn bộ 256 bitstring (đề xuất) hay mẫu ngẫu nhiên?** Với 8
   qubit, duyệt hết rẻ (256 × 3 cách tính), không có lý do gì chỉ lấy mẫu. Xác nhận lại để không ai
   "tối ưu sớm" xuống còn vài chục mẫu.

---

## Tóm tắt executive

- **Sửa lại hoàn toàn phạm vi** so với bản `plan.md` trước: 8-bit không phải 20-bit, closed-form QUBO
  không phải surrogate-fit, 1 mức hành động không phải 4, không polishing — khớp `docs/limitations.md`
  §1 và CLAUDE.md, không phải thiết kế PSS gốc.
- **Blocker lớn nhất: `packages/risk/` chưa implement (34 dòng)** — quantum cần `fixtures.py` tạm
  (theo đúng tiền lệ `qshield_ai/fixtures.py`) để build/test được trong lúc chờ. Rule 17 (chấm lại
  bằng true CVaR) bị chặn cứng tới khi risk có thật.
- **10 file thật cần viết** trong `packages/quantum/` (không đụng `backends/hardware.py`), **4 file**
  trong `packages/pipeline/`.
- **3 bug đã biết** từ `docs/perf/2026-08-04-pipeline-timing.md` cần xử lý trong phạm vi
  `packages/pipeline/`: thiếu `@app.callback()`, `run_id` không dùng chung giữa các chặng, UTF-8
  console crash trên `--help`.
- **8 câu hỏi cần chốt** trước khi code, quan trọng nhất là #1 (risk có ai làm không), #3 (giá trị
  λ₁/λ₂/P) và #6 (pipeline gọi package con kiểu gì — quyết định luôn cách sửa bug run_id).
