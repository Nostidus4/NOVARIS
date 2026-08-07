# Báo cáo benchmark solver Q-SHIELD: Exact vs Classical vs QAOA

**Ngày đo:** 2026-08-07
**Người tổng hợp:** phiên coding / đo solver
**Đối tượng đọc:** nhóm trưởng / owner Quantum + Risk
**Trạng thái bằng chứng:** `NON_BASELINE_RUN`, `NON_FINAL_CONFIG`
**Quy tắc bắt buộc:** không tuyên bố quantum advantage (CLAUDE.md §18). Mọi QAOA chạy trên
`StatevectorSampler` (mô phỏng cổ điển), **không** phải phần cứng lượng tử.

---

## Tóm tắt điều hành (đọc 1 phút)

1. **Trên bài toán production (cash-hedge QUBO), QAOA không thắng classical/exact** về chất lượng
   nghiệm lẫn tốc độ.
2. **20 qubit (baseline `workflow_update`) không chạy nổi QAOA** trên simulator; pipeline đúng phải
   fallback `actual_solver=exact` và báo cáo trung thực.
3. **10 qubit** chạy được QAOA thật: không warm-start thì **thua** exact/classical (gap +2,03%,
   true CVaR giảm 9,87% vs 10,59%). Có warm-start thì hòa — nhưng warm-start **được mớm từ exact**,
   không phải bằng chứng độc lập.
4. Nguyên nhân sâu: QUBO production **gần tuyến tính**, nghiệm tối ưu ở **góc all-1s** → classical
   local search giải trong <1s. Instance hiện tại **không phân biệt được** năng lực solver.
5. Stress-instance synthetic (landscape khó hơn, 232 local minima): QAOA **tìm đúng** nghiệm exact,
   nhưng classical cũng đúng và nhanh hơn ~50.000×. Vẫn **không có khoảng thắng** trên simulator.
6. **Khuyến nghị sản phẩm:** dùng exact + classical + rerank true CVaR làm đường chính; QAOA giữ
   vai trò benchmark/minh họa, không làm engine khuyến nghị cuối.
7. **Notebook narrative đã chạy** (`06_qaoa_scaling_and_depth.ipynb`): exact tăng ~124× từ n=8→16
   (tường \(O(2^n)\)); QAOA tăng \(p\) 1→2 giảm gap 18,4%→16,3% (cải thiện thật, vẫn thua classical
   trên simulator).

---

## 1. Mục tiêu đo và phạm vi

### 1.1. Câu hỏi cần trả lời

- QAOA có tìm được nghiệm tốt hơn / nhanh hơn exact và classical trên QUBO của pipeline không?
- Warm-start có làm méo bằng chứng không?
- Bottleneck runtime nằm ở đâu?
- Có nên đặt quantum computing làm solver chính cho bài cash-hedge này không?

### 1.2. Ba solver được so

| Solver | Bản chất | Vai trò |
|---|---|---|
| **Exact** | Duyệt hết \(2^n\) bitstring trên surrogate NumPy | Ground truth QUBO-level |
| **Classical** | Multi-start 1-bit local search (`coordinate_descent_classical`) | Baseline heuristic cổ điển |
| **QAOA** | `qiskit` QAOA p=1 + COBYLA + `StatevectorSampler` | Ứng viên “quantum” trên simulator |

Classical **không** thay true CVaR. True CVaR / materiality nằm ở bước `rerank-polish` /
`benchmark-true` (Risk). Benchmark solver chỉ so trên **cùng một hàm QUBO**.

### 1.3. Luồng classical (để đọc số cho đúng)

```text
QUBO surrogate
    → điểm xuất phát: all-0, all-1, + N−2 bitstring ngẫu nhiên (mặc định 64 restarts)
    → mỗi điểm: lặp lật 1 bit nếu giảm energy, đến khi kẹt local min
    → chọn energy thấp nhất giữa mọi restart
```

Code: `packages/quantum/src/qshield_quantum/benchmark.py` → `coordinate_descent_classical`.

### 1.4. Warm-start là gì (quan trọng khi đọc bảng)

- **Có warm-start:** Qiskit `WarmStartQAOAOptimizer` + pre-solver classical; workflow còn truyền
  `reference_bitstring = exact.best_feasible_bitstring`. QAOA được **khởi tạo gần đáp án**.
- **Không warm-start:** QAOA bắt đầu từ tham số mặc định theo seed — phép thử trung thực hơn.

---

## 2. Không được trộn các run

| | Run A — baseline scope | Run B — reduced QAOA scope | Run C — stress synthetic |
|---|---|---|---|
| Mục đích | Pipeline sản phẩm 20-bit | Lấy số QAOA thật | Thử landscape khó hơn |
| Candidates / bits | 10 / **20** | 5 / **10** | — / **10** |
| QUBO | Production fitted | Production fitted (scope hạ) | Synthetic frustrated sibling |
| True CVaR? | Có (pipeline) | Có (cùng hash 10-bit) | **Không** — chỉ energy QUBO |
| Artifact | `artifacts/dev/` | `artifacts_bench/{warm,no_warm}_start_run/` | `artifacts_bench/stress_run/` |
| Được dùng cho UAT? | Chỉ khi 3 gate ký; hiện `NON_BASELINE` | Không | Không |

Run B tồn tại **chỉ vì** QAOA 20 qubit không hoàn tất. Tham số tài chính sao chép từ Run A; khác
duy nhất là scope. **Không** suy từ Run B ra hiệu năng 20 qubit. **Không** trộn Run C với số
true-CVaR baseline.

---

## 3. Run A — 20 bit (baseline scope): QAOA không chạy được

| Chặng | Thời gian |
|---|---:|
| fit surrogate | 0,004s |
| verify consistency (sampled, 4.098 states) | 2,444s |
| exact exhaustive (1.048.576 states) | **39,583s** |
| QAOA | **0s — không chạy / timeout** |
| classical local search | 0,500s |
| Quantum stage tổng | **42,531s** |
| Full pipeline 6 chặng | **101,27s** |

- Exact và classical **cùng** bitstring `11111111111111111111` (mọi candidate giảm 30%).
- Energy exact = classical; `classical_gap = 0`.
- Artifact: `requested_solver=qaoa`, `actual_solver=exact`,
  `fallback_reason` ghi QAOA skipped/timeout.

Lịch sử thử QAOA 20 qubit (không seed nào hoàn tất):

| Thử | Cấu hình | Kết quả |
|---|---|---|
| Trước đó | warm-start, maxiter 50, vài seed | >15 phút / seed, bỏ |
| Trước đó | no warm-start, maxiter 10, 1 seed | >13 phút, bỏ |
| 2026-08-07 | no warm-start, shots 1024, maxiter 200, 1 seed | treo **>60 phút**, abort; không ra log xong seed |

**Bottleneck:** không phải exact/classical/pipeline. Nút cổ chai là
`solve_qaoa_one_seed` → `MinimumEigenOptimizer(QAOA).solve` với `StatevectorSampler` trên 20 qubit
(mỗi bước COBYLA = mô phỏng statevector \(2^{20}\) biên độ). Timeout trong code chỉ chặn seed
*sau khi xong*, nên seed đang chạy có thể treo rất lâu nếu không hard-kill.

---

## 4. Run B — 10 bit: số QAOA thật trên QUBO production (scope hạ)

`qubo_hash` chung ba solver:
`2e50ce079c4711f69efe1ec9b21d696308301b63c6aa3a65a3588aacff85a181`.

Exact: 1.024 states, **0,037s**, optimum `1111111111`, E = 0,8510740588.
Classical: **0,144s**, trùng exact, gap 0.

### 4.1. Warm-start vs không warm-start

| | B1 — warm-start | B2 — no warm-start |
|---|---|---|
| Seeds hoàn tất | **10/10** | **1/10** (9 bị timeout sau seed đầu) |
| Bitstring | `1111111111` (đúng) | `1101111111` (sai — Hamming-1 của optimum) |
| Optimality gap | **0%** | **+2,03%** |
| Success prob (mean) | 0,756% | **0%** |
| Runtime / seed | ~4,0s | **337s** |
| Runtime QAOA tổng | 40,4s | 337s |
| `actual_solver` | `qaoa` | `exact` (fallback) |

**Đọc đúng B1:** số đẹp vì warm-start mớm đáp án từ exact. **Không** dùng B1 để nói “QAOA tự tìm
ra optimum”.

**Đọc đúng B2:** phép thử trung thực. QAOA lệch optimum, success_prob = 0 trên 1024 shot, runtime
×84. Cái làm 10-qubit “chạy nhanh” ở B1 chính là warm-start — và warm-start cần exact trước.

### 4.2. Chấm lại bằng true CVaR (bắt buộc theo quy tắc dự án)

Baseline true CVaR 95% trước hành động: `0,0742390541`.

| Solver | Bitstring | True CVaR sau | Giảm CVaR | Materiality (≥1%) |
|---|---|---:|---:|:--:|
| exact | `1111111111` | 0,0663769041 | **10,59%** | PASS |
| classical | `1111111111` | 0,0663769041 | **10,59%** | PASS |
| QAOA B2 (no warm) | `1101111111` | 0,0669084207 | **9,87%** | PASS |
| QAOA B1 (warm) | `1111111111` | 0,0663769041 | 10,59% | PASS |

Exact ≡ classical trên tầng tài chính. QAOA trung thực **thua ~0,72 điểm phần trăm** CVaR
reduction. `ranking_disagreement = 0` trên mẫu 3 nghiệm (QUBO rank khớp true rank) — tín hiệu surrogate
ổn ở scope nhỏ, chưa đủ để kết luận rộng.

---

## 5. Vì sao instance production không phân biệt được solver

Không phải bug QAOA. Landscape QUBO fitted:

| Chỉ số | 10 bit | 20 bit |
|---|---:|---:|
| Dấu linear | toàn âm | toàn âm |
| \|linear\| / \|Q off-diag\| | ~450× | ~378× |
| Optimum | góc `111…1` | góc `111…1` |
| Ý nghĩa surrogate | “giảm càng nhiều càng tốt” | giống vậy |

Classical đi theo cải thiện 1-bit là vào góc. QAOA no-warm dừng ở láng giềng Hamming-1
(`1101111111`, ΔE ≈ 0,017) — gần nhưng chưa đủ. **Không có “khoảng thắng”** để QAOA thể hiện trên
instance này.

---

## 6. Run C — Stress-instance (10 bit, synthetic)

**Mục đích:** trả lời “nếu landscape khó hơn, QAOA có khoảng thắng trước classical không?”
**Không** phải bằng chứng UAT / true-CVaR.

Thiết kế (`tools/qaoa_stress_bakeoff.py`):

- Giữ chiều 10 bit; scale \|linear\| lấy từ surrogate 10-bit thật.
- Linear hỗn dấu + quadratic frustrated dày + soft prefer Hamming weight = 5.
- Landscape đo được: optimum `0010011110` (weight 5, **không** góc); **232** local minima;
  \|lin\|/\|quad\| ≈ 10 (production ≈ 450).

| Solver | Bitstring | Gap | Runtime |
|---|---|---:|---:|
| exact | `0010011110` | 0 | **0,002s** |
| classical yếu (4 restarts) | `0010011110` | 0 | **0,001s** |
| classical mạnh (64 restarts) | `0010011110` | 0 | **0,006s** |
| QAOA no-warm (1 seed, shots 256, maxiter 30) | `0010011110` | 0 | **289s** |

Verdict stress:

- QAOA **khớp exact** (không warm-start) trên bài khó hơn góc → phương pháp *chạy đúng*.
- Classical cũng khớp exact, nhanh hơn ~5×10⁴ lần.
- `qaoa_beats_classical_* = false`. **Vẫn không có advantage** trên simulator 10 qubit.

---

## 7. Sửa kỹ thuật phát hiện trong phiên đo

1. **`qubo_hash` từng không ổn định giữa các run** vì băm cả `run_id`. Đã loại `run_id` khỏi
   payload hash. Kiểm chứng: B1/B2 khác `run_id` nhưng cùng
   `2e50ce07…ff85a181`.
2. **`stage_timings_seconds.total`** từng cộng nhầm counter `verify_checked_states` như thể là
   giây. Đã tách; tổng quantum stage thật ≈ 42,5s (không phải ~4138s).

---

## 8. Kết luận và khuyến nghị gửi nhóm trưởng

### 8.1. Quantum computing có nên là solver chính cho bài này?

**Với bằng chứng hiện tại: chưa nên.**

Lý do ngắn:

| Điều kiện để quantum hữu ích | Thực tế Q-SHIELD |
|---|---|
| Landscape khó, classical kẹt | Production gần tuyến tính, góc tối ưu |
| Exact không khả thi | Exact 20-bit ~40s |
| Classical thua về chất lượng | Classical ≡ exact |
| Runtime trên QPU thật | Chỉ có simulator — QAOA chậm hơn exact |

Đây không phủ nhận tiềm năng QAOA nói chung; đây là kết luận **trên instance và stack hiện tại**.

### 8.2. Khuyến nghị vận hành

1. **Đường chính sản phẩm / demo / UAT (khi gate mở):**
   `exact` (+ classical benchmark) → `rerank-polish` → `benchmark-true` → dashboard.
   Giữ `actual_solver` trung thực; mặc định `--quantum-mode exact` cho 20-bit.
2. **QAOA:** giữ trong pipeline như lớp benchmark / minh họa phương pháp. Báo cáo thua/hòa đúng số.
   Không dùng warm-start-from-exact làm bằng chứng “QAOA thắng”.
3. **Slide / báo cáo nhóm:** tách rõ Run A / B / C; cấm trộn 10-bit QAOA với claim 20-bit baseline.
4. **Nếu sau này muốn tìm “khoảng thắng” thật:** phải đổi hình bài toán (ràng buộc chặt, tương tác
   mạnh, không gian vượt exact) **và** ideally đo trên QPU — không phải chạy lại cùng QUBO góc
   all-1s.

### 8.3. Việc còn mở

- Peak memory (G5) / `reference_hardware` còn `null`.
- Chưa có đủ 10 seed QAOA no-warm ở 10-bit production (seed đầu đã 337s).
- Chưa có seed QAOA 20-bit hoàn tất.
- Surrogate thresholds (TL-014) vẫn PROVISIONAL.
- 3 approval gate (`data_gate`, `scenario_gate`, `product_gate`) chưa ký → mọi số vẫn
  `NON_BASELINE_RUN`.

---

## 9. Notebook narrative (đã chạy) — câu chuyện gửi giám khảo

Notebook: [`notebooks/exploration/06_qaoa_scaling_and_depth.ipynb`](../../notebooks/exploration/06_qaoa_scaling_and_depth.ipynb)
Artifact: `artifacts_bench/narrative_run/` (`exact_scaling.png`, `qaoa_depth_scan.png`,
`narrative_bakeoff.json`).

**Mục đích trình bày:** không phải “QAOA thắng hôm nay”, mà “chúng tôi đo được tường của exact
và biết QAOA cải thiện theo độ sâu — đó là lý do giữ quantum trong kiến trúc”.

### 9.1. Exact scaling \(O(2^n)\) trên stress QUBO

| n | States | Exact (s) | Classical 64-restart (s) | Classical = exact? |
|---|---:|---:|---:|:--:|
| 8 | 256 | 0,0018 | 0,0059 | yes |
| 10 | 1.024 | 0,0027 | 0,0063 | yes |
| 12 | 4.096 | 0,0113 | 0,0080 | yes |
| 14 | 16.384 | 0,0509 | 0,0128 | yes |
| 16 | 65.536 | **0,223** | 0,0114 | yes |

Từ n=8→16, exact tăng ~**124×** (khớp bậc \(2^{8}=256\)); classical gần như phẳng (~ms).
Ngoại suy cùng nhịp (neo n=16 = 0,22s): n=20 ~ 3,6s (cùng bậc với production ~40s khi QUBO khác),
n=30 ~ 1 giờ, n=40 ~ năm. **Exact có tường; classical heuristic chưa chứng minh được chất lượng khi
tường đó tới.**

### 9.2. Quét độ sâu QAOA \(p=1,2\) (stress 10-bit, **no warm-start**)

Smoke `NON_FINAL`: 1 seed, shots=128, maxiter=20.

| Solver | Gap vs exact | Match exact? | Runtime |
|---|---:|:--:|---:|
| exact | 0% | yes | 0,003s |
| classical | 0% | yes | 0,007s |
| QAOA **p=1** | **18,41%** | no | 251s |
| QAOA **p=2** | **16,33%** | no | 496s |

Đọc đúng cho slide:

1. Tăng \(p\) **cải thiện** gap (18,4% → 16,3%) — QAOA không phải hộp đen ngẫu nhiên.
2. Trên simulator 10-bit, classical vẫn thắng về tốc độ và chất lượng.
3. Claim trung thực: *QAOA là ứng viên cho vùng exact không còn khả thi; hôm nay ở 10–20 bit
   simulator, classical/exact vẫn là thước đo đúng.*

---

## 10. Lệnh tái lập

```bash
# Run A — 20 bit, exact-only (đường chính hiện tại)
uv run qshield-pipeline workflow-update \
  --config configs/base.yaml \
  --profile configs/profiles/workflow_update.yaml \
  --override configs/provisional/workflow_update_downstream.yaml \
  --quantum-mode exact

# Run B — 10 bit production-scope (cần regime/scenarios trong artifacts_bench/dev)
BENCH="--config configs/base.yaml --profile configs/profiles/workflow_update.yaml \
  --override configs/provisional/qaoa_benchmark_10bit.yaml"
uv run qshield-risk prepare-workflow $BENCH
uv run qshield-quantum workflow $BENCH                  # warm-start
uv run qshield-quantum workflow $BENCH --no-warm-start  # trung thực
uv run qshield-risk rerank-polish $BENCH
uv run qshield-risk benchmark-true $BENCH

# Run C — stress sibling (solver bakeoff only)
uv run python tools/qaoa_stress_bakeoff.py

# Narrative notebook (scaling + depth)
export MPLCONFIGDIR=.mplconfig IPYTHONDIR=.ipython
uv run jupyter nbconvert --to notebook --execute --inplace \
  notebooks/exploration/06_qaoa_scaling_and_depth.ipynb
```

### Artifact đính kèm

| Run | Thư mục |
|---|---|
| A (20-bit exact path) | `artifacts/dev/optimization/`, `artifacts/dev/risk/true_benchmark.json` |
| B1 warm-start | `artifacts_bench/warm_start_run/` |
| B2 no warm-start | `artifacts_bench/no_warm_start_run/` |
| C stress | `artifacts_bench/stress_run/stress_bakeoff.json` |
| D narrative | `artifacts_bench/narrative_run/` |

Mỗi thư mục B có `qubo_model.json`, `workflow_benchmark.json`, `qaoa_results.json`,
`true_benchmark.json`.

---

## 11. Một dòng gửi nhóm trưởng

> Trên QUBO cash-hedge hiện tại, exact và classical đã trùng nghiệm tối ưu trong vài chục giây;
> QAOA trên simulator không nhanh hơn, không tốt hơn (trừ khi warm-start từ exact), và không chạy
> nổi ở 20 qubit — nên giữ quantum làm lớp benchmark trung thực, không làm engine tối ưu chính.
> Đồng thời notebook scaling cho thấy exact có tường \(O(2^n)\), và tăng độ sâu \(p\) cải thiện gap
> QAOA — đó là lý do kiến trúc vẫn giữ quantum cho vùng bài toán lớn hơn exact chịu nổi.
