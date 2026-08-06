# Workflow Update — Open Inputs and Owner Handoff

Tài liệu này liệt kê các đầu vào còn thiếu để chuyển đường chạy development
`8 mã → Risk giữ 8 → Quantum 16-bit` thành baseline chính thức
`30 mã → Risk chọn top 10 → Quantum 20-bit`.

Đường chạy hiện tại chỉ là `NON_BASELINE_RUN`. Không dùng artifact development làm bằng chứng UAT.
Mọi giá trị trong `configs/provisional/workflow_update_downstream.yaml` là placeholder có công bố,
không phải giá trị đã được owner phê duyệt.

Checklist ngắn để gửi nhóm trưởng và theo dõi quyết định:
`docs/handoffs/team_lead_decision_todolist.md`.

## 0. Registry giá trị provisional đang chạy

Nguồn máy đọc được duy nhất là `configs/provisional/workflow_update_downstream.yaml`, version
`workflow-update-downstream-provisional-v1`. Danh sách dưới đây giúp owner review tác động; khi
thay đổi phải tăng version và chạy lại toàn bộ downstream.

- Runtime: 8 candidates, 2 bit/candidate, 16 decision bits, 137 structured samples và 65.536
  trạng thái exact. Đây là underfill từ dữ liệu hiện có; owner Data là Nguyễn Đỗ Minh Anh. Tác
  động: chưa đo được hành vi chọn top 10 từ universe 30 và không được dùng làm baseline.
- Transaction cost: fee `0.0015`, spread `0.0010`, liquidity penalty `0.0005`;
  `weight_sum_tolerance=1e-8`. Owner Risk là Liêu Hoài Phúc, approver Nguyễn Thị Ánh Ngọc. Tác
  động: thay các số này sẽ đổi candidate rank, true objective, rerank và recommendation.
- Cash target: `target_cash_increment=0.10`; maximum reduction `0.30`. Owners là Nguyễn Anh Tú
  (stress policy) và Liêu Hoài Phúc (Risk), approver Nguyễn Thị Ánh Ngọc. Tác động: cash-budget
  deviation có thể đổi nghiệm tối ưu đáng kể.
- Candidate score: sáu trọng số marginal 10/20/30, baseline contribution, transaction cost và
  liquidity penalty đều tạm bằng `1.0`. Owner Liêu Hoài Phúc. Tác động: thứ tự top-N và coverage
  phụ thuộc trực tiếp vào các trọng số này.
- Canonical objective `(weight, scale)`: CVaR `(1.0, 0.10)`, return sacrifice `(0.25, 0.05)`,
  transaction cost `(0.25, 0.01)`, turnover `(0.05, 0.20)`, liquidity penalty `(0.25, 0.01)`,
  cash-budget deviation `(0.50, 0.10)`. Owner Liêu Hoài Phúc, approver Nguyễn Thị Ánh Ngọc. Tác
  động: đây là target mà surrogate fit; thay bất kỳ giá trị nào làm QUBO cũ mất hiệu lực.
- QAOA: `p=1`, `shots=1024`, COBYLA `maxiter=200`, 10 seed đăng ký trước
  `[101,202,303,404,505,606,707,808,909,1001]`. Owner Đỗ Ngọc Tân, reviewers Liêu Hoài Phúc và
  Nguyễn Thị Ánh Ngọc. Tác động: runtime và chất lượng candidate pool; không được cherry-pick seed.
- Local polishing: zero-action lock, tối đa `±5pp`, final reduction trong `[0,30%]`. Profile đã
  khóa rule nhưng thuật toán/tolerance vẫn cần Risk owner xác nhận.

## 1. Data gate

Owner chính: Nguyễn Đỗ Minh Anh. Approver sản phẩm: Nguyễn Thị Ánh Ngọc.

- Danh sách chính xác 30 mã VN30 tại snapshot `2026-08-03`, ticker vendor và company name.
- Source Registry, quyền sử dụng dữ liệu và checksum/version của universe.
- Evidence adjusted close/corporate action cho từng mã; không chấp nhận gán `close` thành
  `adjusted_close` mà không có bằng chứng.
- `universe_30_asof_20260803.csv`, `data_quality_report.csv` và `eligibility_daily.parquet`.
- Chốt mâu thuẫn ngày: asset train start `2016-01-01` hay `2018-07-02`; test end
  `2026-06-30` hay `2026-07-31`.

Khi có câu trả lời: cập nhật universe/data config và chạy Data Gate. Không thay ticker giả hoặc
padding để đủ top 10.

## 2. Scenario gate

Producer: Nguyễn Anh Tú. Reviewer/approver gate: Liêu Hoài Phúc.

- Xác nhận scenario count 2.000 cho development và 5.000 cho final.
- Phê duyệt validation thresholds và exception policy khi một metric fail.
- Cung cấp `regime_summary.json`, `scenario_manifest.json`, `scenario_validation.csv`.
- Xác nhận cube có shape `(S, 20, 30)`, simple returns, ticker order khớp universe và
  `gate_status=PASS`.

## 3. Transaction cost và accounting

Owner: Liêu Hoài Phúc. Approver: Nguyễn Thị Ánh Ngọc.

- `fee`, thuế/phí bán, `spread`, slippage/liquidity penalty và nguồn căn cứ.
- `weight_sum_tolerance`.
- Low/base/high assumptions dùng cho sensitivity analysis.
- Quy ước liquidity penalty có nằm trong transaction cost hay là objective component riêng để
  tránh double-count.

Khi thay placeholder: chạy lại toàn bộ objective samples, QUBO fit, solver, rerank và polishing.

## 4. Candidate ranking

Owner: Liêu Hoài Phúc. Approver: Nguyễn Thị Ánh Ngọc.

- Công thức chính thức cho `baseline_CVaR_contribution`.
- Trọng số và scaling của marginal CVaR reduction, transaction cost, liquidity và constraint
  penalty trong `net_risk_score`.
- Tie-break sequence và minimum top-10 risk coverage threshold.
- Quy tắc xử lý ticker ineligible hoặc position weight bằng 0.
- Chốt artifact canonical: `candidate_top10.csv`, `candidate_order.json`, hoặc bắt buộc cả hai.

Development behavior hiện tại: `M=min(N_eligible, 10)`. Với 8 mã, cả 8 được giữ và ghi
`UNDERFILLED_CANDIDATES_8_OF_10`; không được diễn giải là top-10 baseline.

## 5. Stress-to-cash policy

Owners: Nguyễn Anh Tú và Liêu Hoài Phúc. Approver: Nguyễn Thị Ánh Ngọc.

- Mapping `p_stress → B_t`, thresholds và policy version.
- Cash-budget tolerance, hard cap và penalty shape.
- Calibration period chỉ gồm train/validation; không dùng test để chỉnh policy.

## 6. Canonical financial objective

Owner: Liêu Hoài Phúc. Approver: Nguyễn Thị Ánh Ngọc.

Chốt trọng số, scale và unit cho:

- CVaR 95%;
- expected-return sacrifice;
- transaction cost;
- turnover;
- liquidity penalty;
- cash-budget deviation.

Mỗi component phải có raw value, scaled value, weight và weighted contribution. Scaling parameters
phải được fit/khóa trước test. Thay weight hoặc scale phải tạo config version mới.

## 7. QUBO surrogate và solver

Technical owner: Đỗ Ngọc Tân. Reviewers: Liêu Hoài Phúc và Nguyễn Thị Ánh Ngọc.

- Surrogate validation thresholds: objective error, rank correlation, top-k recall, feasibility và
  stability.
- Regularization/penalty policy cho formulation four-level; không tái sử dụng penalty K=3 của
  `demo_fast`.
- Danh sách QAOA seeds đăng ký trước, timeout, optimizer budget và warm-start policy.
- Performance budget/reference hardware cho exact 2^20 và QAOA 20 qubit.
- Số validation/random objective samples ngoài 211 structured samples.

Exact phải duyệt đủ 1.048.576 states khi có 10 candidates. QAOA, exact và classical phải dùng cùng
QUBO hash. Không cherry-pick seed và không tuyên bố quantum advantage.

## 8. Rerank, polishing và product gate

Risk owner: Liêu Hoài Phúc. Product owner: Nguyễn Thị Ánh Ngọc.

- Số distinct feasible candidates cần rerank trong khoảng 10–20.
- Tie-break của true financial objective.
- Polishing algorithm/tolerance; zero-action lock và giới hạn ±5pp đã được profile khóa.
- Materiality threshold để gắn trạng thái “không cải thiện”.
- Requirement coverage report, limitations report và UAT evidence.

Baseline chỉ được công bố sau khi `data_gate`, `scenario_gate` và `product_gate` đều có sign-off.

## 9. Việc cần làm sau mỗi approval

1. Thay đúng khóa provisional bằng giá trị/version đã duyệt; không sửa code để nhúng số.
2. Gỡ ID tương ứng khỏi `provisional_overrides`.
3. Chạy lại tests, objective sampling, surrogate validation, exact/QAOA, rerank và polishing.
4. Tạo run mới ở artifact mode `runs`; không ghi đè artifact development cũ.
5. Cập nhật RTM/Test Evidence bằng run ID và reviewer.
