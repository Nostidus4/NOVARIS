# Checklist hỏi nhóm trưởng — `workflow_update`

Mục đích: gom các câu hỏi cần nhóm trưởng điều phối/chốt để chuyển từ đường development hiện tại
`8 mã → 16-bit` sang baseline chính thức `30 mã → dynamic top 10 → 20-bit`.

Trạng thái hiện tại: **`NON_BASELINE_RUN`**. Code downstream đã hoàn thành nhưng các giá trị tài
chính, dữ liệu và ngưỡng nghiệm thu bên dưới chưa được owner phê duyệt. Không dùng kết quả hiện tại
làm bằng chứng UAT/baseline.

Nguồn chi tiết:

- Giá trị tạm và owner: `docs/handoffs/workflow_update_open_inputs.md`
- Phần đã code: `docs/perf/2026-08-06-workflow-update-downstream.md`
- Khoảng trống benchmark: `docs/benchmark_plan.md`

---

## A. Những quyết định đang chặn baseline

### Data — hỏi Minh Anh, Ngọc duyệt

- [ ] **TL-001 — Chốt universe 30 mã.** Danh sách VN30 chính xác tại snapshot `2026-08-03` là gì?
  Cần ticker nội bộ, ticker vendor, company name, nguồn và checksum/version.
  - Output cần nhận: `universe_30_asof_20260803.csv`
  - Nếu chưa có: pipeline tiếp tục dùng 8 mã và luôn là `NON_BASELINE_RUN`.

- [ ] **TL-002 — Chốt bằng chứng adjusted close.** Dùng adjusted close từ nguồn nào? Ai xác nhận
  corporate actions cho từng mã? Có chấp nhận nguồn cross-check miễn phí hay không?
  - Output cần nhận: Source Registry + adjusted-close evidence.
  - Quy tắc bắt buộc: không được tự gán `close = adjusted_close`.

- [ ] **TL-003 — Chốt khoảng thời gian dữ liệu.**
  - Asset train start: `2016-01-01` hay `2018-07-02`?
  - Test end: `2026-06-30` hay `2026-07-31`?
  - Khi chốt: sửa config và tạo data version mới.

- [ ] **TL-004 — Chốt eligibility.** Có giữ các ngưỡng hiện tại không:
  `min_history_sessions=252`, coverage `≥98%`, turnover 20 ngày
  `≥1.000.000.000 VND`? Ai duyệt exception?
  - Output cần nhận: `eligibility_daily.parquet` + reason code cho mã bị loại.

### Scenario — hỏi Tú, Phúc duyệt

- [ ] **TL-005 — Chốt scenario count.** Development = `2.000`, final = `5.000` có được duyệt không?
  Nếu cần cấu hình demo nhanh riêng thì dùng bao nhiêu và gắn nhãn gì?

- [ ] **TL-006 — Chốt Scenario Gate.** Duyệt hay sửa các threshold hiện có cho mean/std/skew/
  kurtosis/quantile/autocorrelation/correlation/tail coverage? Nếu một metric fail thì:
  hard fail, approved exception, hay fallback?
  - Output cần nhận: `scenario_validation.csv`, `scenario_manifest.json`,
    `regime_summary.json`, `gate_status`.

### Risk và tài chính — hỏi Phúc, Ngọc duyệt

- [ ] **TL-007 — Chốt transaction cost.** Giá trị chính thức cho:
  - fee/thuế bán;
  - spread;
  - slippage hoặc liquidity penalty;
  - `weight_sum_tolerance`;
  - bộ low/base/high cho sensitivity.
  - Số tạm đang dùng: fee `0.0015`, spread `0.0010`, liquidity `0.0005`,
    tolerance `1e-8`.

- [ ] **TL-008 — Chốt cách tính liquidity penalty.** Liquidity penalty nằm trong transaction cost,
  là một objective component riêng, hay cả hai? Nếu cả hai thì cách nào tránh double-count?

- [ ] **TL-009 — Chốt stress-to-cash policy.**
  - Mapping `p_stress → target_cash_increment (B_t)` là gì?
  - Ngưỡng, hard cap, tolerance và penalty shape?
  - Số tạm hiện tại: target tăng cash `10%`, maximum reduction mỗi mã `30%`.

- [ ] **TL-010 — Chốt công thức xếp hạng candidate.**
  - Công thức `baseline_CVaR_contribution`;
  - weight/scale cho marginal CVaR 10/20/30%, contribution, cost, liquidity;
  - tie-break;
  - minimum top-10 risk coverage;
  - cách xử lý ticker ineligible hoặc weight = 0.
  - Số tạm hiện tại: sáu score weight đều bằng `1.0`.

- [ ] **TL-011 — Chốt canonical financial objective.** Duyệt weight, scale và unit cho 6 thành phần:
  CVaR, return sacrifice, transaction cost, turnover, liquidity penalty, cash-budget deviation.
  - Câu hỏi quan trọng: ưu tiên giảm CVaR hay bám cash target khi hai mục tiêu xung đột?
  - Mỗi thay đổi phải tăng config version và fit lại QUBO.

### Quantum và Benchmark — hỏi Tân, Phúc/Ngọc review

- [ ] **TL-012 — Chốt cấu hình QAOA final.** Duyệt hay sửa:
  `p=1`, `shots=1024`, COBYLA `maxiter=200`, warm-start và 10 seed
  `[101,202,303,404,505,606,707,808,909,1001]`.
  - Cần chốt riêng cấu hình dev nhanh và final.
  - Cấu hình dev giảm seed/shots phải gắn `NON_FINAL_CONFIG`.

- [ ] **TL-013 — Chốt timeout và performance budget.**
  - Timeout cho một seed và toàn bộ QAOA?
  - Runtime/RAM tối đa chấp nhận cho exact 20-bit và QAOA 20-qubit simulator?
  - Máy/reference hardware nào dùng để báo benchmark?

- [ ] **TL-014 — Chốt ngưỡng Surrogate Gate trước khi xem kết quả final.**
  - MAE/RMSE tối đa;
  - Spearman rank correlation tối thiểu;
  - top-k recall tối thiểu;
  - feasibility/stability threshold.
  - Nếu fail: dừng solver hay có approved exception?

- [ ] **TL-015 — Chốt benchmark bắt buộc.** Có đồng ý benchmark phải gồm:
  exact + QAOA + classical trên cùng `qubo_hash`, distribution đủ 10 seed, success probability,
  feasible rate, optimality gap, runtime/memory và benchmark true-CVaR sau rerank?

### Rerank, polishing và Product Gate — hỏi Phúc/Ngọc

- [ ] **TL-016 — Chốt candidate pool rerank.** Rerank top `10`, `20`, hay số khác distinct feasible
  bitstrings? Tie-break true objective là gì?

- [ ] **TL-017 — Chốt polishing.** Xác nhận:
  zero-action lock, biên `±5pp`, final reduction `[0,30%]`, thuật toán coordinate search và
  tolerance dừng.

- [ ] **TL-018 — Chốt materiality.** CVaR/true objective phải cải thiện tối thiểu bao nhiêu mới gọi
  là “có cải thiện”? Nếu không đạt thì hiển thị cảnh báo hay fallback no-action?

- [ ] **TL-019 — Chốt điều kiện Product Gate.** Ai ký:
  requirement coverage, limitations, dashboard reconciliation, disclaimer và UAT evidence?
  Baseline chỉ được công bố khi `data_gate`, `scenario_gate`, `product_gate` đều có sign-off.

---

## B. Quyết định kỹ thuật nhóm trưởng chỉ cần xác nhận

- [ ] **TL-020 — Xác nhận dynamic underfill.** Khi chưa đủ 10 mã eligible, dùng
  `M=min(N_eligible,10)` (ví dụ 8 mã → 16 bit), gắn `NON_BASELINE_RUN`, không padding ticker giả.

- [ ] **TL-021 — Xác nhận artifact canonical.** Có bắt buộc giữ cả
  `candidate_top10.csv` và `candidate_order.json` không? Đề xuất: **giữ cả hai** — CSV để audit
  ranking, JSON để khóa bit-decoding order/hash.

- [ ] **TL-022 — Xác nhận fallback solver.** Nếu QAOA timeout hoặc không có nghiệm feasible,
  dùng exact làm `actual_solver`, vẫn báo QAOA failure trung thực.

- [ ] **TL-023 — Xác nhận nguyên tắc công bố.** Không tuyên bố quantum advantage; simulator không
  đại diện QPU; exact chỉ chứng minh tối ưu ở tầng QUBO, không phải tối ưu tài chính.

---

## C. Todo của team sau khi nhận quyết định

### Minh Anh — Data

- [ ] Cập nhật universe/config theo TL-001…004.
- [ ] Sinh `universe_30_asof_20260803.csv`, `data_quality_report.csv`,
  `eligibility_daily.parquet`.
- [ ] Chạy và xin ký Data Gate.

### Tú — AI/Scenarios

- [ ] Cập nhật scenario config theo TL-005…006 và cash-policy input từ TL-009.
- [ ] Sinh cube `(S,20,30)` cùng manifest/validation/regime summary.
- [ ] Chạy và xin Phúc ký Scenario Gate.

### Phúc — Risk

- [ ] Thay provisional values theo TL-007…011; tăng config version.
- [ ] Khóa candidate formula, financial objective, cash policy.
- [ ] Chốt true benchmark/rerank/polishing theo TL-015…018.
- [ ] Chạy lại candidate selection → objective samples → true rerank → final accounting.

### Tân — Quantum/Pipeline

- [ ] Instrument runtime để xác định nút thắt QAOA trước khi tối ưu.
- [ ] Hoàn thành các pha trong `docs/benchmark_plan.md`.
- [ ] Khóa QUBO hash/candidate-order hash và solver manifest.
- [ ] Chạy exact đủ `2^20`, QAOA đủ seed và classical baseline.
- [ ] Ghép pipeline full, sinh benchmark/UAT artifacts.

### Ngọc — Product/Approver

- [ ] Ghi quyết định và approver cho TL-001…023.
- [ ] Duyệt limitations/disclaimer và cách trình bày benchmark.
- [ ] Chạy requirement coverage, dashboard reconciliation và UAT.
- [ ] Ký Product Gate hoặc ghi rõ lý do chưa đạt.

---

## D. Mẫu trả lời đề nghị nhóm trưởng dùng

```text
Decision ID:
Quyết định:
Owner thực hiện:
Approver:
Giá trị/config được duyệt:
Nguồn căn cứ:
Deadline:
Điều kiện/exception:
```

Sau mỗi quyết định:

- [ ] Cập nhật đúng khóa trong config, không hard-code trong code.
- [ ] Tăng `config_version`.
- [ ] Gỡ đúng provisional/TBD tương ứng.
- [ ] Chạy lại toàn bộ chặng chịu ảnh hưởng.
- [ ] Tạo run mới trong `artifacts/runs/`, không ghi đè evidence cũ.
- [ ] Cập nhật RTM/test evidence bằng run ID và reviewer.
