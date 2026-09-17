# NOVARIS: Phương án triển khai Quantum-assisted Candidate Generation

---

## 1. Quyết định định hướng

Nhóm **có thể chuyển vai trò của Quantum** từ:

> QAOA cạnh tranh trực tiếp với classical về tốc độ và khả năng tìm nghiệm tối ưu.

sang:

> QAOA tạo một phân phối ứng viên có cấu trúc; thuật toán classical tiếp tục lọc, chấm lại và tinh chỉnh các ứng viên đó bằng hàm mục tiêu tài chính thật.

Tên nên sử dụng:

> **QAOA-assisted candidate generation for classical portfolio optimization**

Việc này **không đổi bài toán tài chính cốt lõi**. NOVARIS vẫn phải giảm tail-risk của danh mục, tuân thủ constraints, kiểm soát chi phí và return sacrifice. Chỉ cách tổ chức nhánh tối ưu được thay đổi.

Không được xóa hoặc viết lại kết quả benchmark cũ. Kết quả “QAOA không thắng classical trực tiếp” vẫn là một phát hiện hợp lệ. Nhánh hybrid là **một giả thuyết nghiên cứu mới**, phải đăng ký protocol mới và đánh giá ngoài mẫu; không dùng nó để thay đổi tiêu chí sau khi đã nhìn thấy kết quả.

## 2. Ý tưởng dễ hiểu

Thuật toán classical giống như một người leo núi: nếu được đặt gần thung lũng tốt, nó có thể nhanh chóng đi tới một nghiệm rất tốt; nếu bắt đầu ở vùng kém, nó có thể dừng ở cực tiểu cục bộ.

Trong hướng mới:

1. QAOA không cần tự tìm đúng nghiệm tối ưu cuối cùng.
2. QAOA sinh nhiều bitstring, ưu tiên các vùng có năng lượng thấp.
3. Risk Engine loại nghiệm vi phạm và chấm lại bằng true CVaR/cost/return.
4. Classical local polishing bắt đầu từ các nghiệm tốt đó.
5. Hệ thống chỉ ghi nhận đóng góp Quantum nếu kết quả cuối tốt hơn một pipeline classical được cấp ngân sách tương đương.

Vì vậy, câu hỏi nghiên cứu mới không phải là: “QAOA có nhanh và chính xác hơn classical không?”

mà là: “Trong cùng ngân sách ứng viên hoặc ngân sách tính toán, việc thêm ứng viên do QAOA sinh có giúp pipeline classical tìm được nghiệm tài chính tốt hơn, ổn định hơn hay đa dạng hơn so với các cách khởi tạo classical không?”

## 3. Đánh giá bằng chứng 1,11% / 4,79% / 5,84%

Kết quả được trình bày hiện nay là một **tín hiệu exploratory đáng theo đuổi**:

- không gian 16-bit có `2^16 = 65.536` bitstring;
- QAOA được cho là chỉ bao phủ khoảng 1,9% không gian;
- sau classical polishing, QAOA-seeded có gap 1,11%;
- random-seeded có gap 4,79%;
- local-search classical có gap 5,84%;
- QAOA-seeded thắng 5/5 danh mục được thử.

Nhưng các con số này **chưa đủ để phê duyệt claim**, vì repository local chưa có artifact tái lập tương ứng. Tân cần làm rõ:

1. 1,11%/4,79%/5,84% là mean, median hay best-of-run?
2. Numerator thật của 1,9% là bao nhiêu bitstring độc nhất? `1,9% x 65.536` không phải số nguyên, nên phải báo `unique_count / 65.536` thay vì chỉ làm tròn phần trăm.
3. Pool tính trên mọi bitstring hay chỉ bitstring feasible?
4. Các duplicate từ nhiều shots/seeds được tính một lần hay nhiều lần?
5. “Optimum” là optimum của QUBO surrogate hay true financial objective?
6. Cả ba nhánh có cùng candidate count, số lần gọi objective, polishing steps và timeout không?
7. Năm danh mục là danh mục nhà đầu tư thật có consent, danh mục synthetic dùng dữ liệu thật, hay năm biến thể của cùng một portfolio/date?
8. Có kết quả per-portfolio trước và sau polishing hay chỉ có số tổng hợp?

Với 5 chiến thắng trên 5 instance độc lập, kiểm định dấu hai phía đơn giản cho `p=0,0625`; mẫu này vẫn quá nhỏ cho kết luận xác nhận ở mức 5%. Nếu năm instance dùng cùng date/scenario thì tính độc lập còn yếu hơn. Vì đây là giả thuyết được hình thành sau khi nhìn kết quả, không dùng kiểm định một phía để làm đẹp kết luận.

Ngoài ra, benchmark local cũ cho thấy ở 16-bit exact duyệt đủ 65.536 trạng thái mất khoảng 0,223 giây và coordinate-descent classical mất khoảng 0,0114 giây, cùng tìm đúng optimum QUBO. Do đó:

- nếu “optimum tuyệt đối” mới vẫn là QUBO 16-bit, QAOA chưa mang giá trị vận hành;
- nếu true objective rất đắt và QAOA giúp chọn ít điểm đáng chấm hơn, đóng góp candidate generation mới có thể có ý nghĩa;
- nếu exact đang được đưa vào pool trước polishing, không thể quy kết kết quả tốt cho QAOA.

Trong bài toán minimization, không viết “đạt optimum cao hơn”. Cách viết đúng là **objective thấp hơn**, **optimality gap nhỏ hơn**, hoặc **đạt nghiệm gần optimum hơn**.

## 4. Kiến trúc đích

```text
Portfolio + Scenario + Policy
        |
        v
Risk Candidate Selection
        |
        v
QUBO Surrogate + Feasibility Contract
        |
        +----------------------+-----------------------+
        |                      |                       |
        v                      v                       v
 QAOA sampler          Uniform/stratified       Classical multistart
 QAOA_POOL             RANDOM_POOL              CLASSICAL_POOL
        |                      |                       |
        +----------------------+-----------------------+
                               |
                               v
                  Source-preserving deduplication
                               |
                               v
             Compliance filter + True-objective scoring
                               |
                               v
                  Same bounded classical polishing
                               |
                               v
                  Paired benchmark + recommendation
```

Nguyên tắc bất biến:

- Exact chỉ là reference, không được bí mật đưa nghiệm exact vào `QAOA_POOL`.
- Mỗi candidate giữ nguồn: seed, shot/probability, raw rank, feasibility và hashes.
- QUBO energy chỉ dùng đánh giá surrogate/solver; recommendation chọn theo true financial objective.
- Cùng polishing operator, neighborhood và budget cho mọi nguồn.
- Báo cả raw candidate và polished result để tách đóng góp của bộ sinh khỏi đóng góp của classical.
- Nếu QAOA timeout, classical pipeline vẫn chạy; `attempted_solver` và `actual_solver` phải đúng.

## 5. Những gì code hiện tại đã có thể tái sử dụng

| Thành phần | Code hiện tại | Có thể giữ | Cần thay đổi |
|---|---|---|---|
| QAOA sampling | `qshield_quantum/solvers/qaoa.py` | `QaoaSample`, per-seed result, energy/probability/feasible | Xuất full measured distribution hoặc một artifact lossless riêng; top-20 không đủ cho distribution claim |
| Workflow Quantum | `qshield_quantum/workflow.py` | exact, QAOA, classical benchmark, hashes/timing | Tách pool theo nguồn; không merge exact và QAOA trước attribution |
| Candidate pool | `_merge_candidate_pool()` | Dedup và source tags là nền tốt | Hiện khởi tạo pool bằng exact rồi mới thêm QAOA; phải tạo `exact_reference`, `qaoa_pool`, `random_pool`, `classical_pool` độc lập |
| True reranking | `qshield_risk/rerank.py::rerank_candidates()` | Chấm true objective và deterministic ordering | Chạy cùng interface cho từng pool; xuất pre-polish table |
| Polishing | `qshield_risk/rerank.py::polish_reductions()` | Giới hạn +/-5% và khóa zero-action giúp attribution rõ | Bổ sung evaluation count, runtime, trajectory/stop reason; dùng cùng budget cho mọi nguồn |
| Financial benchmark | `qshield_risk/true_benchmark.py` | CVaR, cost, turnover, return sacrifice | Mở từ best-one-per-solver sang pool-level và hybrid ablation |

Vấn đề attribution quan trọng nhất: `_merge_candidate_pool()` hiện đưa `exact.top_feasible_candidates` vào trước rồi trộn samples QAOA. Nếu dùng pool này để nói “QAOA + polish đạt 1,11%”, kết luận có thể bị nhiễm bởi nghiệm exact. Nhánh hybrid mới phải tách artifact nguồn ngay từ đầu.

## 6. Artifact và contract cần bổ sung

### 6.1. Artifact phân phối QAOA

Tạo `qaoa_distribution.parquet`, mỗi hàng là một `(experiment_id, instance_id, seed, bitstring)`:

```text
experiment_id
instance_id
run_id
seed
bitstring
qubo_energy
probability
estimated_count
feasible
candidate_order_hash
action_map_hash
qubo_hash
shots
p
optimizer
maxiter
backend
warm_start
```

Không chỉ lưu top-20 nếu muốn đánh giá distribution. Kiểm tra:

- probability sum theo seed xấp xỉ 1 trong tolerance;
- bitstring length và endian đúng contract;
- không trộn hashes;
- giữ cả infeasible mass để đo feasibility rate;
- `unique_feasible_count` được tính sau dedup;
- nếu chỉ export truncated distribution, bắt buộc có `retained_probability_mass` và không gọi đó là full coverage.

### 6.2. Pool riêng theo nguồn

```text
candidate_pools/
  exact_reference.parquet
  qaoa_raw.parquet
  random_matched.parquet
  classical_multistart.parquet
  qaoa_unique_feasible.parquet
  random_unique_feasible.parquet
  classical_unique_feasible.parquet
```

Mỗi hàng sau decode thêm:

```text
source_method
source_seed
source_rank
raw_probability
effective_action_hash
is_duplicate_after_decode
constraint_status
constraint_reasons
true_objective_before_polish
true_cvar_before_polish
```

Dedup bằng **effective action sau decode và rounding**, không chỉ raw bitstring. Hai bitstring tạo cùng lệnh thực thi không phải hai ý tưởng đầu tư khác nhau.

### 6.3. Polishing trace

Tạo `polishing_results.parquet`:

```text
source_method
start_candidate_hash
start_true_objective
final_candidate_hash
final_true_objective
objective_improvement
true_objective_evaluations
iterations
wall_seconds
active_set_changed
zero_action_lock_respected
stop_reason
```

Primary attribution nên giữ active set do candidate chọn; nếu cho phép đổi active set thì đó là một experiment khác. Nếu polishing tự do đổi gần như toàn bộ nghiệm, kết quả cuối chủ yếu thuộc classical optimizer.

### 6.4. Báo cáo tổng hợp

Tạo:

- `hybrid_benchmark_manifest.json`;
- `hybrid_benchmark_per_instance.csv`;
- `hybrid_benchmark_summary.json`;
- `hybrid_attempts.jsonl` gồm cả crash/timeout;
- `hybrid_claim_checklist.json`;
- biểu đồ empirical CDF của gap và paired uplift, nhưng report số phải dùng được dù không có biểu đồ.

Mỗi artifact bắt buộc mang `portfolio_hash`, `scenario_hash`, `candidate_order_hash`, `action_map_hash`, `qubo_hash`, code commit, dependency lock hash và machine manifest.

## 7. Ma trận thí nghiệm công bằng

### 7.1. Các track tối thiểu

| Track | Candidate source | Polishing | Mục đích |
|---|---|---|---|
| `T0_EXACT_REFERENCE` | Duyệt toàn bộ khi khả thi | Không dùng làm seed cho track khác | Biết optimum ở instance nhỏ |
| `T1_LOCAL_ONLY` | Classical multistart | Same bounded polish hoặc chính optimizer đã đăng ký | Baseline classical trực tiếp |
| `T2_RANDOM_HYBRID` | Uniform/stratified feasible random | Same bounded polish | Kiểm soát việc chỉ có thêm nhiều điểm bắt đầu |
| `T3_QAOA_HYBRID` | QAOA samples | Same bounded polish | Đo incremental value của QAOA candidates |
| `T4_CLASSICAL_EXTRA_COMPUTE` | Classical sampler/search dùng compute tăng thêm bằng QAOA | Same bounded polish | Kiểm tra lợi ích có chỉ do thêm ngân sách hay không |
| `T5_WARM_START_QAOA` | QAOA có seed classical | Same bounded polish | Nhánh hybrid khác; không gộp với QAOA thuần |

Không đưa exact candidate vào T2–T5. Exact chỉ cung cấp `J*`/reference ở instance nhỏ.

### 7.2. Hai chế độ matching

Không thể đảm bảo vừa cùng thời gian vừa cùng số candidate nếu chi phí mỗi phương pháp rất khác. Vì vậy chạy hai view:

1. **Candidate-budget matched:** cùng `B` effective unique feasible candidates được true-objective score.
2. **Compute-budget matched:** cùng tổng wall time và giới hạn objective evaluations; báo số candidate mỗi nhánh thực tạo được.

QAOA phải thắng ít nhất theo một view đã đăng ký và không thất bại nghiêm trọng ở view còn lại mới có lý do thực dụng. Nếu chỉ thắng candidate-budget nhưng chậm hơn hàng nghìn lần, claim chỉ là đặc tính phân phối thuật toán.

### 7.3. Random baseline không được quá yếu

- Random sampling phải cùng feasible domain hoặc dùng cùng repair/filter rule.
- Có uniform random và, nếu cần, stratified theo số active assets/total reduction.
- Mỗi random replicate dùng seed đăng ký trước.
- `classical multistart` có đủ restarts/evaluations tương xứng.
- Nếu thêm simulated annealing/tabu/genetic solver, cùng constraints và budget; không tune classical sơ sài rồi tune QAOA kỹ.

### 7.4. Instance set

Một `portfolio-date instance` là một ca kiểm thử hoàn chỉnh được xác định bởi **một danh mục đầu vào + một ngày chốt dữ liệu**, kèm regime, scenario set, financial objective và constraints tương ứng. Nhiều scenario seed trên cùng một portfolio-date không được tự động tính thành nhiều quan sát độc lập.

Năm danh mục hiện tại giữ làm `EXPLORATORY_SET`, không dùng làm final confirmation. Tập xác nhận đề xuất:

- tối thiểu 30 `portfolio-date` instances;
- có diversified, banking-concentrated, high-volatility, high-cash, do-not-sell và liquidity-constrained;
- bao phủ Normal, Volatile, Stress nếu Scenario Gate từng regime đạt;
- nhiều scenario seeds/block lengths đã đăng ký;
- không tạo nhiều bản sao rất giống nhau rồi coi là quan sát độc lập;
- portfolio thật phải có consent; portfolio synthetic trên dữ liệu thật phải ghi đúng nhãn.

Nếu không đủ 30 instance độc lập, vẫn báo kết quả exploratory với sample size thật; không dùng CI đẹp từ hàng nghìn scenarios để thay thế số portfolio-date độc lập.

## 8. Metric cần báo

### 8.1. Chất lượng candidate trước polishing

Với bài toán minimization:

```text
absolute_gap = J(candidate) - J(reference)
relative_gap = absolute_gap / max(abs(J(reference)), epsilon)
near_optimal_rate(epsilon) = count(gap <= epsilon) / unique_feasible_count
feasible_probability_mass = sum(probability of feasible measured states)
unique_feasible_coverage = unique_feasible_count / total_feasible_states
```

Tách metric ở hai tầng:

- `qubo_energy_gap`: QAOA có đi vào vùng tốt của surrogate không;
- `true_objective_gap`: candidate đó có thật sự tốt theo CVaR/cost/return không.

Không so relative energy gap giữa các QUBO có constant offset/scale khác nhau mà không normalize contract. Luôn báo absolute gap và per-instance rank.

Thêm:

- unique feasible candidates;
- duplicate rate;
- entropy/effective sample size của distribution;
- top-k probability mass;
- Hamming/action diversity;
- recall của true top-k khi exact reference khả thi;
- novelty so với classical pool.

“Phân bố tốt hơn” chỉ được dùng khi metric cụ thể cho thấy mass/rank/gap tốt hơn, không dựa vào hình nhìn có vẻ tập trung.

### 8.2. Đóng góp sau polishing

```text
hybrid_uplift = J(best classical-only final) - J(best QAOA-seeded final)
```

`hybrid_uplift > 0` nghĩa QAOA-assisted tốt hơn theo objective đã chọn. Báo thêm:

- gap trước/sau polish theo từng nguồn;
- fraction instances QAOA-assisted thắng/hòa/thua;
- median/mean uplift, dispersion và paired confidence interval;
- số lần gọi true objective;
- time/memory/error rate;
- winner source;
- polishing dependency;
- stability qua QAOA seeds.

### 8.3. Giá trị tài chính

Primary selection không dùng QUBO energy. Phúc phải chấm:

- CVaR 95%, robustness 97,5%/99%;
- expected return sacrifice;
- transaction cost và liquidity impact;
- turnover và cash after;
- worst drawdown;
- hard-constraint violations;
- materiality của cải thiện sau chi phí.

Nếu QAOA-assisted cải thiện QUBO gap nhưng không cải thiện true CVaR sau cost, đóng góp chưa đi tới giá trị sản phẩm.

## 9. Chiến lược số qubit thấp

Workflow sản phẩm chính vẫn là **Risk chọn top 10 mã, mỗi mã 2 bit, tổng 20 bit và 1.048.576 tổ hợp**. Các thử nghiệm 16 bit bên dưới là research track giảm scope để kiểm định giả thuyết; chúng không thay thế hoặc được trình bày như kết quả hoàn thành workflow 20 bit.

### Phương án A: 16-bit research track

- Risk chọn 8 candidates, mỗi mã 2 bit, tổng 16 bit.
- Exact duyệt 65.536 state làm reference.
- Dùng để kiểm candidate-distribution hypothesis và debug attribution.
- Không dùng kết quả 8 mã để tuyên bố đã giải đầy đủ bài toán 10/15 mã nếu coverage Risk không đạt.

Ưu điểm: chạy được local, có ground truth.
Nhược điểm: exact/classical quá mạnh, giá trị vận hành Quantum rất khó chứng minh.

### Phương án B: QAOA giải neighborhood nhỏ trong bài toán lớn

```text
Classical master solution trên full candidates
→ chọn một subproblem 4–8 mã theo rule đăng ký
→ giữ các biến ngoài subproblem cố định
→ QAOA sinh neighborhood candidates 8–16 bit
→ nhúng candidate trở lại full solution
→ true-objective rerank + bounded polish
→ lặp tối đa R vòng
```

So với cùng decomposition trong đó subproblem được giải bằng random/classical. Rule chọn subproblem không được dùng thông tin exact future winner. Báo full-solution objective và toàn bộ compute, không chỉ subproblem energy.

Ưu điểm: phù hợp hạn chế qubit local và vẫn tác động bài toán lớn.
Nhược điểm: đóng góp dễ thuộc classical master/decomposition; cần ablation nghiêm ngặt.

### Khuyến nghị

Làm **Phương án A trước** để xác nhận giả thuyết trong môi trường có ground truth. Chỉ khi attribution/fairness pass mới làm Phương án B. Không tăng số bit chỉ để làm classical khó, và không giảm candidates dưới Risk Gate chỉ để QAOA chạy được.

## 10. Tiêu chí PASS theo từng tầng

### Gate H0: Reproducibility

PASS khi có code commit, dependency lock, configs, 5 portfolio definitions, raw distributions, exact references, seeds và hashes. Chưa có artifact thì số trong slide chỉ là claim cần xác minh.

### Gate H1: Attribution

PASS khi:

- exact/QAOA/random/classical pools tách nguồn;
- không exact contamination;
- same polishing + evaluation accounting;
- báo pre/post polish;
- source của final winner truy được.

### Gate H2: Fairness

PASS khi có cả candidate-budget và compute-budget view; baseline classical đủ mạnh; không cherry-pick seed/portfolio; timeout/failure được giữ.

### Gate H3: Distribution signal

Exploratory PASS khi QAOA pool cho candidate gap/rank tốt hơn matched random/classical trên tập phát triển. Điều này chỉ xác nhận tín hiệu thuật toán, chưa phải product value.

### Gate H4: Confirmation

Trước fresh holdout phải khóa:

- instance/date list hoặc rule sinh list;
- primary metric;
- materiality threshold;
- seeds/budgets;
- tie/missing/failure rule;
- statistical test/CI.

Confirmation PASS đề xuất khi có ít nhất 30 instance đủ đa dạng, median paired uplift dương và material, 95% paired CI không chứa 0, đồng thời không phát sinh constraint/cost/latency vượt policy. Nếu không đủ sample, kết luận `INCONCLUSIVE`, không tự hạ gate.

### Gate H5: Product value

PASS khi QAOA-assisted cải thiện **true financial objective sau chi phí** so với matched strong-classical baseline với latency/failure chấp nhận được. Nếu chỉ cải thiện QUBO energy thì giữ nhãn research contribution.

### Gate H6: Quantum claim

Simulator study không đủ cho quantum advantage. Dù H0–H5 pass, cách nói vẫn là `QAOA-assisted` hoặc `hybrid algorithmic contribution` cho tới khi có protocol tài nguyên/hardware phù hợp.

## 11. Kế hoạch thực hiện cho Tân

### Pha 0: Đóng băng thí nghiệm đã có

1. Gửi code commit/branch và lệnh tái lập 5 danh mục.
2. Gửi per-instance rows, không chỉ slide tổng hợp.
3. Ghi rõ exact optimum ở QUBO hay true objective.
4. Ghi số pool tuyệt đối, duplicate/feasible definition.
5. Đặt `EXPLORATORY_NON_BASELINE`, không sửa kết quả sau khi chạy lại.

### Pha 1: Sửa contract/pool

1. Export distribution lossless.
2. Tách `exact_reference`, `qaoa_pool`, `random_pool`, `classical_pool`.
3. Thêm candidate provenance + hashes.
4. Test contamination, probability sum, dedup và deterministic ordering.
5. Không dùng exact pool làm input hybrid.

### Pha 2: Pool-level Risk benchmark

1. Mở `true_benchmark.py` để nhận danh sách candidate theo nguồn.
2. Chạy compliance và true-objective scoring cùng code path.
3. Chạy `polish_reductions()` cùng max adjustment/evaluation budget.
4. Xuất pre/post polish, evaluation count và winner origin.
5. Phúc review CVaR/cost/constraints.

### Pha 3: Fair baseline harness

1. Implement random matched pool với seeds đăng ký.
2. Implement classical multistart/extra-compute track.
3. Chạy candidate-budget view.
4. Chạy compute-budget view.
5. Chạy warm-start riêng; không gộp.

### Pha 4: Mở rộng instance và thống kê

1. Giữ 5 instance làm exploratory.
2. Đăng ký ít nhất 30 portfolio-date instances mới/đủ độc lập.
3. Chạy qua regimes/scenario configs đã pass.
4. Báo paired table, CI, wins/ties/losses và failures.
5. Không tune sau khi nhìn holdout; thay đổi tạo experiment version mới.

### Pha 5: Tích hợp sản phẩm có kiểm soát

1. Classical-only luôn là đường recommendation chính/fallback.
2. QAOA branch chạy async có timeout.
3. Chỉ thêm candidate nếu hashes/gates hợp lệ.
4. UI hiện `QAOA candidate source`, `classical polished`, simulator, status/fallback.
5. Nếu Quantum không tạo incremental material value, không để tăng latency của flow người dùng.

## 12. Test tối thiểu cần bổ sung

### Unit tests

- full distribution probability mass;
- stable bit order/endian;
- same bitstring dedup across seeds;
- same effective action dedup after decode/rounding;
- exact never appears in QAOA-only pool;
- source tags survive rerank/polish;
- active-set lock and max-adjustment respected;
- evaluation count and runtime nonnegative;
- hash mismatch hard fail;
- no feasible QAOA candidates handled without fake success.

### Integration tests

- T1–T4 use same portfolio/scenario/config;
- candidate-budget equality;
- compute-budget termination;
- forced QAOA timeout -> classical result with correct identity;
- rerank uses canonical financial objective;
- pre/post polish outputs reconcile;
- exact solution never leaks into hybrid track;
- dashboard/export match artifact values.

### Statistical regression tests

- rerunning same seed reproduces pool/hash within documented backend behavior;
- input order changes do not silently change semantic actions;
- adding duplicate samples does not improve unique coverage;
- metric aggregation uses per-instance pairing, not pooling all candidates as independent observations.

## 13. RACI

| Việc | Responsible | Reviewer/Approver |
|---|---|---|
| QAOA distribution, pool separation, harness, runtime | Tân | Phúc review; Ngọc scope |
| True CVaR, cost, constraints, polishing fairness | Phúc | Ngọc |
| Scenario seeds/regime validity/instance dates | Tú | Phúc + Ngọc |
| Portfolio provenance/data quality | Minh Anh | Ngọc |
| Claim, UAT và quyết định promote | Ngọc | Team cung cấp evidence |

Ngọc không cần tự xác nhận bug Qiskit, true-CVaR implementation hay candidate distribution. Tân/Phúc/Tú phải ký phần kỹ thuật thuộc họ; Ngọc phê duyệt phạm vi, claim và release dựa trên evidence.

## 14. Trade-off

| Lợi ích | Đánh đổi |
|---|---|
| Vai trò Quantum thực tế hơn, không cần thắng classical trực tiếp | Khó quy attribution vì kết quả cuối do classical polishing |
| Có thể chạy subproblem ít qubit | Có thể không đại diện full candidate set/Risk Gate |
| QAOA distribution có thể khám phá basin khác | Simulator cost cao, classical sampling mạnh có thể làm tương tự |
| True-objective rerank giảm rủi ro surrogate | Tốn nhiều lần tính CVaR, cần matched evaluation budget |
| Giữ classical fallback giúp hệ thống sử dụng được | Quantum có thể chỉ còn vai trò nghiên cứu, không tạo product value |

Đây không phải điểm yếu cần che giấu. Nếu QAOA-assisted không tạo lift ngoài mẫu, kết luận đúng là: **Quantum được tích hợp và đánh giá nghiêm túc nhưng chưa tạo incremental decision value ở scope hiện tại**.

## 15. Cách trình bày được phép

Nếu mới có 5 instance:

> Trên 5 instance exploratory, QAOA-seeded classical polishing tạo nghiệm gần reference hơn các baseline khởi tạo được thử. Kết quả là tín hiệu ban đầu về chất lượng candidate distribution, chưa phải xác nhận ngoài mẫu.

Nếu H0–H5 pass:

> Trong protocol đã đăng ký, việc bổ sung QAOA candidates cải thiện true financial objective sau cùng một classical polishing budget so với các candidate generators đối chứng. Kết quả phản ánh đóng góp của pipeline hybrid trên simulator, không phải quantum advantage.

Không được viết:

- “Quantum tìm được optimum cao hơn classical.”
- “QAOA thắng classical” khi phần thắng xảy ra sau classical polishing mà không có attribution.
- “Quantum chỉ duyệt 1,9% nhưng tốt hơn exact” nếu exact vẫn tìm optimum nhanh hơn.
- “5 danh mục thật” nếu chỉ là portfolio synthetic trên real market data.
- “Quantum advantage” hoặc “quantum speedup” từ StatevectorSampler.

## 16. Phản hồi ngắn gửi Tân

> Tui đồng ý cho chuyển vai trò Quantum sang QAOA-assisted candidate generation, còn classical chịu trách nhiệm polishing và recommendation cuối. Đây là hướng hợp lý hơn so với cố chứng minh QAOA nhanh/chính xác hơn classical trực tiếp.
>
> Tuy nhiên, mình không bỏ benchmark tốc độ và chất lượng; chúng chuyển thành metric phụ bắt buộc. Metric chính là incremental lift của `QAOA candidates + same classical polish` so với `random/classical candidates + same polish`, trên true financial objective sau cost và constraints.
>
> Trước khi chốt số 1,11%/4,79%/5,84%, ông tách exact/QAOA/random/classical pools, gửi artifact per-portfolio và raw distribution. Code hiện tại đang merge exact vào candidate pool và thường cắt top-20, nên chưa đủ attribution cho claim 1,9%. Giữ 5 danh mục là exploratory, sau đó preregister tập xác nhận lớn hơn và hai benchmark candidate-budget/compute-budget.
>
> Nếu pass, mình trình bày đây là đóng góp hybrid QAOA-assisted trên simulator, không phải quantum advantage. Nếu không pass ngoài mẫu, mình vẫn báo trung thực Quantum chưa tạo incremental decision value ở scope hiện tại.

## 17. Quyết định cần Tân phản hồi

Tân cần trả lời bằng evidence, không chỉ “đồng ý/không đồng ý”:

- [ ] Cung cấp đường dẫn artifact của 5 instance và lệnh chạy lại.
- [ ] Xác nhận optimum thuộc QUBO hay true objective.
- [ ] Cung cấp số unique/feasible/duplicate tuyệt đối tạo nên 1,9%.
- [ ] Xác nhận pool 1,11% không chứa exact candidate.
- [ ] Cung cấp bảng per-instance raw -> polished cho cả ba nguồn.
- [ ] Cung cấp candidate count, objective evaluations, polishing iterations, wall time và RAM từng track.
- [ ] Chấp nhận giữ cả candidate-budget và compute-budget comparison.
- [ ] Chấp nhận giữ 5 instance là exploratory và preregister confirmation set.
- [ ] Đề xuất code changes/tests cụ thể theo Pha 1–3.
- [ ] Ghi rõ simulator backend và không dùng quantum-advantage claim.

Chỉ sau khi các mục trên có artifact và reviewer xác nhận, Ngọc mới chuyển proposal này từ `DRAFT_RESEARCH_PROPOSAL` sang `APPROVED_EXPERIMENT`. Việc phê duyệt thí nghiệm không đồng nghĩa phê duyệt baseline/release.
