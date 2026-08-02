---
document_id: QSHIELD-AC-001
document_title: Q-SHIELD Acceptance Criteria Specification
document_version: 1.0
document_status: Baseline Candidate
product_name: Q-SHIELD
team_name: NOVARIS
parent_scope_document: QSHIELD-PSS-001-v1.0
parent_requirements_document: QSHIELD-PRS-001-v1.0
parent_user_story_document: QSHIELD-US-001-v1.0
acceptance_owner: Nguyễn Thị Ánh Ngọc
qa_owner: Liêu Hoài Phúc
technical_owner: Đỗ Ngọc Tân
language: vi-VN
last_updated: 2026-08-02
---

# Q-SHIELD — ACCEPTANCE CRITERIA SPECIFICATION

## Tiêu chí nghiệm thu cho hệ thống Quantum–AI hỗ trợ quản trị tail risk danh mục cổ phiếu

**Đội dự án:** NOVARIS  
**Product Owner:** Nguyễn Thị Ánh Ngọc  
**QA/Risk Owner:** Liêu Hoài Phúc  
**Tài liệu nguồn:** `QSHIELD-PSS-001 v1.0`, `QSHIELD-PRS-001 v1.0`, `QSHIELD-US-001 v1.0`  
**Trạng thái:** Baseline Candidate

---

# 1. MỤC ĐÍCH

Tài liệu này xác định các điều kiện quan sát được để quyết định một User Story hoặc Product Requirement của Q-SHIELD đã được triển khai đúng hay chưa. Acceptance Criteria được viết theo cấu trúc **Given–When–Then**, có mã truy xuất, mức chặn release và evidence cần lưu.

Acceptance Criteria khác Test Case:

- **Acceptance Criteria** mô tả điều kiện sản phẩm phải đáp ứng.
- **Test Case** mô tả dữ liệu test cụ thể, các bước thực thi, expected value và actual value.
- Một Acceptance Criterion có thể cần nhiều Test Cases: happy path, negative, boundary, fallback và regression.

Tài liệu này không cho phép nhóm kết luận “pass” chỉ vì code chạy không lỗi. Một criterion chỉ pass khi outcome đúng, constraints đúng, evidence đầy đủ và kết quả truy xuất được.

---

# 2. QUY ƯỚC NGHIỆM THU

## 2.1. Mức độ

| Mức | Ý nghĩa |
|---|---|
| P0 | Release blocker; fail một criterion P0 thì không được phát hành final recommendation |
| P1 | Bắt buộc cho R1/UAT; chỉ defer bằng quyết định Product Owner có limitation |
| P2 | Challenger/enhancement; không chặn core R1 |

## 2.2. Trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| NOT_RUN | Chưa kiểm thử |
| PASS | Expected outcome đạt và evidence hợp lệ |
| FAIL | Có sai lệch outcome hoặc thiếu điều kiện bắt buộc |
| BLOCKED | Không chạy được do dependency chưa sẵn sàng |
| DEFERRED | Được phê duyệt hoãn, có lý do và release impact |
| NOT_APPLICABLE | Chỉ dùng khi có phê duyệt và giải thích; không áp dụng cho P0 core |

## 2.3. Evidence tối thiểu

Mỗi lần thực hiện Acceptance Criteria phải lưu:

```yaml
acceptance_evidence:
  acceptance_id: AC-XXX-000
  test_case_ids: [TC-XXX-000]
  requirement_ids: [PR-XXX-000]
  user_story_ids: [US-XXX-000]
  run_id: string|null
  environment: string
  data_version: string|null
  config_version: string|null
  expected_result: string
  actual_result: string
  status: PASS|FAIL|BLOCKED|DEFERRED
  evidence_paths: [string]
  tester: string
  reviewer: string
  executed_at: datetime
  defect_id: string|null
```

## 2.4. Nguyên tắc tolerance

- Tolerance tài chính và số học phải lấy từ Config Registry.
- Không được tăng tolerance chỉ để làm test pass.
- Mọi thay đổi tolerance phải tạo config version mới và chạy regression.
- Ký hiệu `εw` là tolerance tổng tỷ trọng; `εp` là tolerance tổng probability; các tolerance khác nằm trong approved config.

## 2.5. Test fixtures chuẩn

| Fixture | Mục đích |
|---|---|
| FIX-PORT-VALID | Danh mục hợp lệ có tối thiểu 10 held-eligible positions |
| FIX-PORT-INVALID | Ticker trùng, weight âm, tổng weight sai, ngày sai |
| FIX-DATA-LEAK | Dataset có record sau evaluation date được cố ý cài vào |
| FIX-DATA-LISTING | Mã chưa niêm yết/chưa đủ 252 phiên tại ngày đánh giá |
| FIX-REGIME | Market features có output probabilities kiểm chứng được |
| FIX-SCENARIO | Scenario cube nhỏ, shape và expected statistics đã biết |
| FIX-RISK | Synthetic losses có VaR/CVaR expected values theo Financial Specification |
| FIX-CANDIDATE | 12–15 assets có score/tie đã thiết kế trước |
| FIX-QUBO | QUBO nhỏ có nghiệm exact biết trước và QUBO 20-bit baseline |
| FIX-ACCOUNTING | Portfolio synthetic có proceeds, cost, cash và NAV expected values |
| FIX-FALLBACK | Backend QAOA được mô phỏng timeout/fail |
| FIX-UI | Validated completed-run artifact package |

---

# 3. ACCEPTANCE CRITERIA — RUN VÀ PORTFOLIO INTAKE

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-RUN-001 | US-RUN-001; PR-RUN-001–004 | P0 | Portfolio có ticker hợp lệ, position/cash không âm, evaluation date hợp lệ | Người dùng gửi request | Hệ thống chấp nhận, chuẩn hóa về internal decimal weights, tạo `run_id` duy nhất và lưu immutable input artifact | Portfolio request, validation log, run manifest |
| AC-RUN-002 | US-RUN-001; PR-RUN-002 | P0 | Cùng một danh mục được nhập một lần bằng value và một lần bằng weight tương đương | Hai request được chuẩn hóa | Internal weights của hai run bằng nhau trong `εw` | Normalization unit test |
| AC-RUN-003 | US-RUN-002; PR-RUN-005 | P0 | Input có ticker trùng | Người dùng submit | Request bị từ chối với `ERR_RUN_DUPLICATE_TICKER`; không khởi chạy Data/HMM/Scenario | Error response, module log |
| AC-RUN-004 | US-RUN-002; PR-RUN-005 | P0 | Input có weight hoặc cash âm | Người dùng submit | Request bị từ chối; field và giá trị vi phạm được chỉ rõ | Negative-input test evidence |
| AC-RUN-005 | US-RUN-002; PR-RUN-005–006 | P0 | Tổng stock weights và cash ngoài `εw` | Người dùng submit | Hệ thống báo tổng hiện tại, tổng yêu cầu và không tự normalize âm thầm | Validation report |
| AC-RUN-006 | US-RUN-002; PR-RUN-006 | P0 | Input chứa ticker ngoài approved universe | Người dùng submit | Hệ thống không tự loại ticker; trả error/warning theo approved policy và yêu cầu xác nhận/sửa | Input diff, response evidence |
| AC-RUN-007 | US-RUN-003; PR-RUN-007 | P1 | Người dùng chọn development mode | Run bắt đầu | Manifest ghi requested/actual scenario count = 2.000 và gắn development config | Run manifest |
| AC-RUN-008 | US-RUN-003; PR-RUN-007 | P1 | Người dùng chọn final mode | Run bắt đầu | Manifest ghi requested scenario count = 5.000; không dùng development-only config nếu không có fallback disclosure | Run manifest, config hash |
| AC-RUN-009 | US-RUN-004; PR-RUN-008, PR-RUN-012 | P1 | Một pipeline đang chạy | Module hoàn tất hoặc fail | State transition đúng thứ tự, có timestamp, producer và message; UI phản ánh cùng trạng thái | State-transition log, UI capture |
| AC-RUN-010 | US-RUN-005; PR-RUN-009 | P0 | Một run đã `COMPLETED` | Người dùng tạo what-if từ run đó | Hệ thống tạo run ID mới; artifacts run cũ không thay đổi checksum | Old/new manifests, checksums |
| AC-RUN-011 | US-RUN-006; PR-RUN-010 | P0 | Sau eligibility chỉ còn dưới 10 held-eligible positions | Pipeline đến Candidate Gate | Baseline risk có thể hoàn tất; Quantum 20-bit bị chặn với `INSUFFICIENT_QUANTUM_CANDIDATES`; không padding assets | Risk output, error/status artifact |
| AC-RUN-012 | PR-RUN-011; PR-OPS-005 | P0 | Một critical module fail giữa pipeline | Orchestrator xử lý lỗi | Artifacts trước lỗi còn để debug; không tạo final recommendation; run status không phải `COMPLETED` | Failure manifest, absence of final output |

---

# 4. ACCEPTANCE CRITERIA — DATA, UNIVERSE VÀ ELIGIBILITY

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-DAT-001 | US-DAT-001; PR-DAT-001–004 | P0 | Approved Universe Registry được nạp | Data run bắt đầu | Registry có đúng 30 unique tickers, snapshot date, source, version, approval status và checksum | Universe Registry validation |
| AC-DAT-002 | US-DAT-001; PR-DAT-002–003 | P0 | Universe v1 đã dùng trong run cũ | Universe được thay đổi | Hệ thống tạo universe version mới; run cũ vẫn trỏ v1 và tái lập được | Version history, manifests |
| AC-DAT-003 | US-DAT-002; PR-DAT-005–007 | P0 | Dataset thiếu field bắt buộc hoặc sai type | Data validation chạy | Data Gate fail với `ERR_DATA_SCHEMA`; model pipeline không chạy | DQ report, orchestrator log |
| AC-DAT-004 | US-DAT-002; PR-DAT-006–007 | P0 | Dataset có duplicate `date+ticker` | Data validation chạy | Duplicate được phát hiện, định vị và Data Gate fail hoặc xử lý theo approved rule có evidence | Duplicate report |
| AC-DAT-005 | US-DAT-002; PR-DAT-007 | P0 | Dataset có price không dương, negative volume, `NaN` hoặc `Inf` ở field critical | Data validation chạy | Mỗi lỗi có count và affected keys; không chuyển record lỗi âm thầm xuống model | DQ report |
| AC-DAT-006 | US-DAT-002; PR-DAT-008 | P0 | Có corporate action fixture | Adjusted-price pipeline chạy | Return series không chứa artificial jump do corporate action theo expected fixture | Corporate-action regression test |
| AC-DAT-007 | US-DAT-003; PR-DAT-011–014 | P0 | FIX-DATA-LEAK chứa record sau evaluation date | Feature pipeline chạy | Test phát hiện leakage và phát hành `ERR_DATA_TEMPORAL_LEAKAGE`; run bị chặn | Temporal test output |
| AC-DAT-008 | US-DAT-003; PR-DAT-012 | P0 | Rolling features được tính tại ngày `t` | So sánh với reference implementation chỉ dùng lịch sử | Feature values khớp trong tolerance; không centered window/backfill từ tương lai | Feature comparison |
| AC-DAT-009 | US-DAT-003; PR-DAT-013–014 | P0 | Config train/validation/test đã khóa | Model selection chạy | Không record test xuất hiện trong training/calibration manifests | Split manifest, date assertions |
| AC-DAT-010 | US-DAT-004; PR-DAT-015–016 | P0 | Cùng universe tại hai evaluation dates khác nhau | Eligibility Engine chạy | Eligible pool có thể khác theo ngày; mỗi kết quả chỉ dùng dữ liệu có sẵn tại ngày đó | Two-date eligibility outputs |
| AC-DAT-011 | US-DAT-005; PR-DAT-017–018 | P0 | FIX-DATA-LISTING có mã chưa niêm yết hoặc chưa đủ lịch sử | Eligibility Engine chạy | Mã bị loại với reason code phù hợp; không có synthetic pre-listing returns | Eligibility report |
| AC-DAT-012 | US-DAT-004; PR-DAT-019 | P0 | Một ticker eligible nhưng portfolio weight bằng 0 | Candidate pool được tạo | Ticker không được đưa vào action candidate pool | Candidate-pool artifact |
| AC-DAT-013 | US-DAT-004; PR-DAT-020 | P1 | Eligibility Engine hoàn tất | Report được tạo | Report có universe count, eligible count, held-eligible count, excluded counts và reason breakdown | Eligibility summary |
| AC-DAT-014 | US-DAT-006; PR-DAT-009–010 | P1 | Một completed run được mở để audit | Auditor xem metadata | Có source ID, acquisition/update date, data version và rights note; không có credential/token | Source Registry, secret scan |

---

# 5. ACCEPTANCE CRITERIA — MARKET REGIME/HMM

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-REG-001 | US-REG-003; PR-REG-001–004 | P0 | Market-level train 2016–2022 và candidate config tồn tại | HMM selection pipeline chạy | Các cấu hình state 2, 3, 4, 5 được đánh giá trên toàn bộ registered seeds hoặc failure được log | Model-selection manifest |
| AC-REG-002 | US-REG-003; PR-REG-004 | P0 | Candidate runs hoàn tất | Selection report được tạo | Mỗi candidate có log-likelihood, AIC, BIC, convergence, occupancy và stability | Selection report |
| AC-REG-003 | US-REG-003; PR-REG-005–006 | P0 | Một model có AIC tốt nhất nhưng stability/interpretability không đạt | Model selection quyết định | Model không được tự động chọn chỉ vì AIC; rationale ghi rõ trade-off | Decision artifact |
| AC-REG-004 | US-REG-003; PR-REG-007 | P0 | Validation 2023 khả dụng | HMM candidates được đánh giá ngoài train | Validation metrics được lưu riêng; test 2024–2026 không tham gia selection | Model manifest |
| AC-REG-005 | US-REG-004; PR-REG-008–009 | P1 | Selected HMM đã fit | State labels được gắn | Mỗi state có return, volatility, drawdown profile; stress label dựa profile chứ không dựa state index | State-profile report |
| AC-REG-006 | US-REG-002; PR-REG-010 | P0 | Regime inference trả probabilities | Validation chạy | Mỗi probability nằm trong `[0,1]`; tổng probabilities bằng 1 trong `εp` | Probability assertions |
| AC-REG-007 | US-REG-002; PR-REG-011 | P0 | Stress state được approved | `p_stress` được xuất | `p_stress` đúng probability của stress state, không phải hard label | Regime output comparison |
| AC-REG-008 | US-REG-001; PR-REG-012 | P0 | Evaluation date là `t` | Inference chạy | Input observations đều có date `≤t` | Inference data manifest |
| AC-REG-009 | US-REG-001; PR-REG-013 | P1 | Inference thành công | Output được lưu | Có run ID, model version, feature version, selected state, label, probabilities và quality flags | `regime_output` artifact |
| AC-REG-010 | US-REG-005; PR-REG-014 | P1 | HMM primary không hội tụ | Fallback logic chạy | Chỉ approved fallback được dùng; run ghi primary failure, fallback model và actual model version | Fallback log |
| AC-REG-011 | US-REG-005; PR-REG-015 | P0 | Không có primary hoặc fallback model đạt gate | Pipeline tiếp tục | Scenario conditioning bị chặn; không có final recommendation | Failure manifest |
| AC-REG-012 | US-REG-001; PR-UI-002 | P1 | Valid regime artifact tồn tại | Dashboard mở run | State label, probabilities và evaluation date khớp artifact; probabilities không bị làm tròn khiến tổng hiển thị gây hiểu nhầm | UI reconciliation evidence |

---

# 6. ACCEPTANCE CRITERIA — SCENARIO ENGINE

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-SCN-001 | US-SCN-001; PR-SCN-001 | P0 | Champion config đã approved | Scenario Engine chạy | Model được dùng là regime-conditioned moving-block bootstrap; actual model ghi trong manifest | Scenario manifest |
| AC-SCN-002 | US-SCN-002; PR-SCN-002 | P0 | Development mode | Generation hoàn tất | Có đúng 2.000 paths nếu không fallback; actual count được lưu | Shape assertion, manifest |
| AC-SCN-003 | US-SCN-002; PR-SCN-002 | P0 | Final mode | Generation hoàn tất | Có đúng 5.000 paths nếu không fallback; nếu fallback count khác phải gắn disclosure và không dùng làm final baseline khi chưa phê duyệt | Shape assertion |
| AC-SCN-004 | US-SCN-001; PR-SCN-003–004 | P0 | `S` scenarios và `N` assets | Cube được lưu | Shape đúng `[S,20,N]`; ticker-order artifact có đúng `N` unique tickers | Scenario schema test |
| AC-SCN-005 | US-SCN-001; PR-SCN-005–006 | P0 | Regime condition và block-length config tồn tại | Bootstrap sampling chạy | Blocks tuân theo approved conditioning policy; block length thuộc approved set | Sampling audit |
| AC-SCN-006 | US-SCN-005; PR-SCN-007–008 | P0 | Scenario run hoàn tất | Manifest được kiểm tra | Có seed, model version, conditioning regime, block length, ticker order và config hash | Scenario manifest |
| AC-SCN-007 | US-SCN-003; PR-SCN-009 | P0 | Cube có injected `NaN`, `Inf` hoặc sai shape | Scenario validation chạy | Quality Gate fail, chỉ rõ vị trí/vấn đề và không chuyển cube lỗi sang Risk Engine | Validation report |
| AC-SCN-008 | US-SCN-003; PR-SCN-010 | P0 | Generated scenarios và historical validation data tồn tại | Statistical validation chạy | Report có moments, volatility, autocorrelation, cross-asset correlation và tail quantiles theo approved metrics | Scenario Validation Report |
| AC-SCN-009 | US-SCN-003; PR-SCN-011 | P1 | Normal- và stress-conditioned sets tồn tại | So sánh regime behavior | Stress scenarios có profile theo acceptance rule; nếu không, gate fail hoặc warning theo config | Regime-consistency report |
| AC-SCN-010 | US-SCN-003; PR-SCN-012–013 | P0 | Một metric vượt threshold | Quality Gate xử lý | Run bị chặn hoặc chuyển đúng approved fallback; không âm thầm bỏ metric | Gate decision log |
| AC-SCN-011 | US-SCN-004; PR-SCN-014 | P2 | CVAE challenger fail | Champion pipeline chạy | Core run vẫn hoàn tất bằng bootstrap; CVAE failure được log và không đổi champion status | Challenger log |
| AC-SCN-012 | US-SCN-004; PR-SCN-015 | P1 | CVAE có metric tốt hơn một phần | Yêu cầu thay champion | Champion chỉ thay khi toàn bộ required validation và Decision Log approval tồn tại | Model Registry history |

---

# 7. ACCEPTANCE CRITERIA — RISK ENGINE

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-RSK-001 | US-RSK-001; PR-RSK-001 | P0 | Synthetic return scenarios | Chuyển sang loss | Mọi loss bằng `-return`; sign convention khớp Financial Specification | Unit test |
| AC-RSK-002 | US-RSK-001; PR-RSK-002 | P0 | Portfolio weights và scenario ticker order khác thứ tự | Risk Engine chạy | Engine map đúng ticker; kết quả khớp reference và không dựa vị trí ngầm | Mapping test |
| AC-RSK-003 | US-RSK-001; PR-RSK-003–006 | P0 | FIX-RISK có expected VaR/CVaR | Risk functions chạy | VaR/CVaR 95%, 97,5%, 99% khớp expected values trong tolerance | Risk unit tests |
| AC-RSK-004 | US-RSK-001; PR-RSK-004 | P0 | Config primary confidence = 95% | Objective được tạo | CVaR 95% là primary component; 97,5%/99% chỉ là robustness outputs | Objective breakdown |
| AC-RSK-005 | US-RSK-001; PR-RSK-005 | P1 | Valid scenario cube | Baseline risk chạy | Output có expected return, maximum drawdown và approved metrics với units | Risk result |
| AC-RSK-006 | US-RSK-002; PR-RSK-007 | P1 | Scenario count và confidence level đã biết | Tail metric được tính | Output báo đúng tail observations thực tế được dùng | Tail-count assertion |
| AC-RSK-007 | US-RSK-002; PR-RSK-008 | P0 | CVaR 99% được hiển thị | Risk result/report được tạo | Có confidence interval và stability warning khi tail sample dưới approved threshold | Risk report |
| AC-RSK-008 | US-RSK-003; PR-RSK-009 | P0 | Approved cost config | Một action plan được đánh giá | Transaction cost trả total và breakdown theo fee/tax/slippage components | Cost calculation test |
| AC-RSK-009 | US-RSK-003; PR-RSK-010 | P0 | Cost config thay đổi version | Cùng action được tính lại | Kết quả thay đổi theo config; code không chứa conflicting hard-coded value | Config-injection test |
| AC-RSK-010 | US-RSK-003; PR-RSK-011 | P0 | Một portfolio change fixture | Turnover được tính ở sampling, re-ranking và UI | Ba kết quả bằng nhau trong tolerance và cùng unit | Cross-module reconciliation |
| AC-RSK-011 | US-RSK-003; PR-RSK-012–013 | P1 | Liquidity proxy và low/base/high cost configs | Sensitivity chạy | Output có source, direction, scale và kết quả ba assumptions | Sensitivity report |
| AC-RSK-012 | PR-RSK-014–016 | P0 | Một action vector | Canonical financial objective chạy | Output có raw, scaled, weight và weighted contribution cho từng component | Objective result |
| AC-RSK-013 | PR-RSK-017–018 | P0 | Scaling/weights đã khóa trước test | Test evaluation chạy | Manifest dùng approved version; không recalibrate trên test | Config/model manifests |
| AC-RSK-014 | PR-RSK-019 | P0 | Action vi phạm constraint | Objective chạy | Scalar objective và violations được trả riêng; violation không bị che chỉ bằng penalty score | Objective schema test |
| AC-RSK-015 | PR-RSK-020 | P1 | Risk run hoàn tất | Artifact được lưu | Có metric definitions, units, confidence levels, scenario count, config hash và run ID | `risk_result.json` validation |

---

# 8. ACCEPTANCE CRITERIA — CANDIDATE SELECTION VÀ STRESS POLICY

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-CAN-001 | US-CAN-001; PR-CAN-001 | P0 | Held-eligible assets và common baseline scenarios | Marginal CVaR reduction được tính | Mỗi asset được đánh giá trên cùng portfolio/scenario basis; output có unit và sign rõ | Candidate metrics |
| AC-CAN-002 | US-CAN-002; PR-CAN-002–004 | P0 | Approved score weights | Candidate score được tính | Score bằng approved combination của risk reduction, cost và illiquidity; components lưu riêng | Score unit test |
| AC-CAN-003 | US-CAN-001; PR-CAN-005 | P0 | Có ít nhất 10 held-eligible assets | Selection chạy | Output có đúng 10 unique tickers | Candidate-order schema test |
| AC-CAN-004 | US-CAN-001; PR-CAN-006 | P0 | Cùng data và config | Selection chạy lặp lại | Danh sách và thứ tự giống nhau | Determinism test |
| AC-CAN-005 | US-CAN-002; PR-CAN-007 | P1 | FIX-CANDIDATE có score ties | Tie-break chạy | Thứ tự khớp approved tie-break sequence và reason được lưu | Tie-break test |
| AC-CAN-006 | US-CAN-001; PR-CAN-008 | P0 | Selection hoàn tất | `candidate_order.json` được kiểm tra | Có rank, ticker, current weight, score components, final score và config version | Artifact validation |
| AC-CAN-007 | US-CAN-003; PR-CAN-009 | P0 | Risk contributions cho eligible universe | Coverage được tính | Coverage khớp approved formula và nằm trong valid domain | Coverage unit test |
| AC-CAN-008 | US-CAN-003; PR-CAN-010–011 | P1 | Coverage dưới threshold | Pipeline xử lý | Warning xuất hiện; sensitivity run có ID/config riêng; baseline 20-bit không bị thay âm thầm | Warning, manifests |
| AC-CAN-009 | US-CAN-004; PR-CAN-012 | P0 | `p_stress` và approved policy | `B_t` được tính | Output đúng target cash increment tương ứng policy version | Policy unit test |
| AC-CAN-010 | US-CAN-004; PR-CAN-013 | P0 | Một dãy `p_stress` tăng dần | Policy áp dụng | Dãy `B_t` không giảm | Monotonicity test |
| AC-CAN-011 | US-CAN-004; PR-CAN-014 | P0 | Policy config được nạp | Run bắt đầu | Threshold, target, hard cap và tolerance đều tồn tại; thiếu critical field làm Gate fail | Config schema validation |
| AC-CAN-012 | US-CAN-004; PR-CAN-015 | P0 | Test data được giữ riêng | Policy calibration chạy | Calibration manifest chỉ chứa train/validation dates; không có test dates | Calibration manifest |

---

# 9. ACCEPTANCE CRITERIA — OBJECTIVE SAMPLING VÀ QUBO

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-QUB-001 | US-QNT-001–002; PR-QUB-001 | P0 | Ordered 10 candidates | Encoding được tạo | Mỗi candidate có đúng hai bit và tổng cộng đúng 20 unique bit positions | Encoding artifact |
| AC-QUB-002 | US-QNT-002; PR-QUB-002 | P0 | Mỗi bit pair `00`, `10`, `01`, `11` | Decode chạy | Mức giảm lần lượt bằng 0%, 10%, 20%, 30% của vị thế hiện tại | Exhaustive mapping test |
| AC-QUB-003 | US-QNT-002; PR-QUB-003 | P0 | Bitstring thiếu/thừa bit hoặc chứa ký tự khác 0/1 | Validation chạy | Bitstring bị từ chối với structured error | Negative bitstring tests |
| AC-QUB-004 | US-QNT-002; PR-QUB-004 | P0 | Toàn bộ action combinations trong fixture | Encode rồi decode | Output actions bằng input actions cho mọi case | Round-trip test |
| AC-QUB-005 | US-QNT-002; PR-QUB-005 | P0 | UI sort order thay đổi | Bitstring được hiển thị/decode | Ticker-action mapping vẫn theo `candidate_order.json` | UI/backend mapping test |
| AC-QUB-006 | US-QNT-003; PR-QUB-006 | P0 | Candidate action vector | Objective sample được tính | Sampler gọi canonical Risk Engine objective; kết quả khớp direct call | Function-contract test |
| AC-QUB-007 | US-QNT-003; PR-QUB-007 | P0 | 20 binary variables | Structured sampling hoàn tất | Có tối thiểu 211 unique evaluations gồm intercept, 20 main và 190 pairwise effects | Sample-design audit |
| AC-QUB-008 | US-QNT-003; PR-QUB-008 | P0 | Fit và validation sampling chạy | Datasets được lưu | Không có bitstring overlap ngoài deliberate reference cases; split policy được ghi | Sampling manifest |
| AC-QUB-009 | US-QNT-003; PR-QUB-009–010 | P0 | Objective samples tồn tại | Schema validation chạy | Mỗi row có bitstring, actions, components, scalar objective, violations, seed và policy version | Sample schema test |
| AC-QUB-010 | US-QNT-003; PR-QUB-011–012 | P0 | Approved samples | Surrogate được fit | QUBO package có coefficients, constant, scales, penalties, candidate order, config hash | QUBO artifact validation |
| AC-QUB-011 | US-QNT-004; PR-QUB-013 | P0 | Held-out validation samples | Surrogate evaluation chạy | Report có objective error, rank correlation, top-k recall, feasibility metric và stability | Surrogate report |
| AC-QUB-012 | US-QNT-004; PR-QUB-014 | P0 | Thresholds đã pre-register | Test set được mở | Threshold version có timestamp trước test evaluation | Registry audit |
| AC-QUB-013 | US-QNT-004; PR-QUB-015 | P0 | Một required surrogate metric fail | Orchestrator xử lý | Phát hành `ERR_QUBO_SURROGATE_VALIDATION`; valid QAOA run không được khởi tạo | Failure log |
| AC-QUB-014 | PR-QUB-016 | P0 | Penalty/regularization thay đổi | QUBO build lại | QUBO version/hash đổi; run cũ giữ coefficients cũ | Version regression |
| AC-QUB-015 | US-QNT-007; PR-QUB-017 | P0 | Exact, QAOA và classical jobs được tạo | Job configs được kiểm tra | Tất cả tham chiếu cùng deterministic QUBO hash | Solver job manifests |

---

# 10. ACCEPTANCE CRITERIA — SOLVERS VÀ QUANTUM

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-SLV-001 | US-QNT-005; PR-SLV-001–002 | P0 | QUBO 20-bit hợp lệ | Exact brute force chạy | Đánh giá đúng 1.048.576 states hoặc exact method có proof tương đương; trả global QUBO optimum | Counter/log, exact result |
| AC-SLV-002 | US-QNT-005; PR-SLV-003 | P0 | Exact run hoàn tất | Output được lưu | Có best bitstring, best energy, feasibility, runtime, QUBO hash và solver version | Exact artifact |
| AC-SLV-003 | US-QNT-005; PR-SLV-004 | P0 | Exact result được trình bày | Report/dashboard mở | Nhãn là “QUBO exact optimum”; không gọi là global financial optimum nếu surrogate chưa exact | Content review |
| AC-SLV-004 | US-QNT-006; PR-SLV-005 | P0 | Approved primary quantum config | QAOA chạy | Algorithm là Warm-start QAOA p=1; actual depth được lưu | QAOA manifest |
| AC-SLV-005 | PR-SLV-006 | P2 | p=2 challenger được bật | Challenger chạy/fail | Kết quả tách khỏi p=1 baseline; failure không chặn R1 | Challenger evidence |
| AC-SLV-006 | US-QNT-006; PR-SLV-007 | P1 | Final QAOA config | Solver chạy | Sử dụng 1.024 shots và tối thiểu 10 registered seeds trừ approved override | Solver manifests |
| AC-SLV-007 | US-QNT-006; PR-SLV-008 | P0 | Mỗi QAOA seed hoàn tất | Artifact được kiểm tra | Có optimizer, initial point, depth, shots, backend, packages, runtime và status | Per-seed artifacts |
| AC-SLV-008 | US-QNT-007; PR-SLV-009 | P0 | QAOA và exact results | Benchmark chạy | QUBO hashes giống nhau; khác hash làm benchmark fail | Benchmark validator |
| AC-SLV-009 | US-QNT-006; PR-SLV-010 | P0 | Có nhiều seed với chất lượng khác nhau | Summary được tạo | Summary chứa toàn bộ registered seeds và aggregate statistics; không chỉ seed tốt nhất | Seed coverage audit |
| AC-SLV-010 | US-QNT-001; PR-SLV-011 | P0 | QAOA sampling hoàn tất | Result được lưu | Có measured bitstrings và count/probability; tổng probability/count nhất quán shots | Distribution test |
| AC-SLV-011 | US-QNT-007; PR-SLV-012–013 | P0 | Exact, QAOA, classical results cùng QUBO | Benchmark được tạo | Có best feasible energy, optimality gap, feasible rate, optimum sampling probability và runtime | Benchmark report |
| AC-SLV-012 | US-QNT-007; PR-SLV-014 | P0 | Runtime comparison được hiển thị | Content review | Hardware/backend, simulator status và caveat được ghi; không tuyên bố speed advantage sai | Report review |
| AC-SLV-013 | US-QNT-008; PR-SLV-015 | P0 | FIX-FALLBACK gây QAOA timeout/fail | Fallback chạy | Exact/classical actual solver được dùng, status `COMPLETED_WITH_FALLBACK`, reason và solver labels rõ | Fallback run artifacts |

---

# 11. ACCEPTANCE CRITERIA — TRUE RE-RANKING, POLISHING VÀ ACCOUNTING

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-FIN-001 | US-FIN-001; PR-FIN-001–002 | P0 | QAOA/exact/classical candidates | Consolidation chạy | Candidate pool chứa distinct feasible bitstrings, giữ solver provenance và probability/count | Candidate pool artifact |
| AC-FIN-002 | US-FIN-001; PR-FIN-003–004 | P0 | Top candidate pool | True evaluation chạy | 10–20 candidates được tính true CVaR, return, cost, turnover, liquidity, cash deviation và violations | Re-ranking table |
| AC-FIN-003 | US-FIN-001; PR-FIN-005 | P0 | Surrogate-best khác true-best | Final coarse selection chạy | True-best feasible candidate được chọn theo approved financial objective, không chọn surrogate-best mặc định | Selection evidence |
| AC-FIN-004 | US-FIN-001; PR-FIN-006 | P1 | Re-ranking hoàn tất | Report được tạo | Có surrogate rank, true rank và disagreement metrics | Re-ranking report |
| AC-FIN-005 | US-FIN-002; PR-FIN-007 | P0 | Một ticker có Quantum action 0% | Polishing chạy | Final action ticker đó vẫn đúng 0% | Zero-lock unit/integration test |
| AC-FIN-006 | US-FIN-002; PR-FIN-008–009 | P0 | Quantum action 10%, 20% hoặc 30% | Polishing chạy | Final action nằm trong interval ±5 điểm phần trăm, không dưới 0 hoặc trên 30% | Boundary tests |
| AC-FIN-007 | US-FIN-002; PR-FIN-010 | P0 | Cùng candidate và scenarios | Polishing objective được tính | Polishing dùng canonical true financial objective và cùng constraints | Function-call trace |
| AC-FIN-008 | US-FIN-002; PR-FIN-011 | P0 | Polishing hoàn tất | Output được lưu | Có bits, quantum action, polished action, absolute delta, before/after objective | Polishing artifact |
| AC-FIN-009 | US-FIN-003; PR-FIN-012 | P1 | Final output tồn tại | Dependency metric được tính | Report tách improvement do Quantum và do polishing; vượt threshold tạo warning | Dependency report |
| AC-FIN-010 | US-FIN-004; PR-FIN-013–014 | P0 | Position value và reduction được biết | Gross proceeds được tính | Proceeds bằng position value nhân reduction, không coi reduction là điểm % NAV | Accounting unit test |
| AC-FIN-011 | US-FIN-004; PR-FIN-015 | P0 | Gross proceeds và synthetic transaction cost | Cash/NAV update chạy | `NAV_after = NAV_before - cost`; `Cash_after = Cash_before + proceeds - cost` | FIX-ACCOUNTING test |
| AC-FIN-012 | US-FIN-004; PR-FIN-016 | P0 | Final portfolio được chuẩn hóa trên NAV sau cost | Reconciliation chạy | Tổng stock weights + cash weight bằng 1 trong `εw` | Weight-sum assertion |
| AC-FIN-013 | US-FIN-004; PR-FIN-017 | P0 | Boundary actions và positions | Constraint validation chạy | Không weight âm, không short, không reduction trên 30%, không bán vượt vị thế | Constraint tests |
| AC-FIN-014 | US-FIN-004; PR-FIN-018 | P0 | Accounting fixture cố ý sai | Final Gate chạy | Phát hành `ERR_FIN_ACCOUNTING`; dashboard không hiển thị recommendation như hợp lệ | Gate failure evidence |
| AC-FIN-015 | US-FIN-005–006; PR-UI-017 | P0 | CVaR_after không thấp hơn CVaR_before theo approved materiality rule | Final result hiển thị | UI/report ghi “không cải thiện” hoặc warning trung thực; không dùng success styling/claim | UI/report evidence |

---

# 12. ACCEPTANCE CRITERIA — DASHBOARD VÀ REPORTING

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-UI-001 | US-UI-001; PR-UI-001–008 | P1 | FIX-UI completed-run package | Dashboard mở | Có đủ Portfolio, Regime, Risk, Candidates, Quantum, Final, Benchmark và Audit/Limitations sections | UI checklist |
| AC-UI-002 | US-UI-002; PR-UI-005–007 | P0 | Run có raw và polished actions | Action table hiển thị | Hai cột tách biệt, có delta; người dùng không thể nhầm polished là raw Quantum | UI review |
| AC-UI-003 | US-UI-003; PR-UI-009 | P0 | Valid run artifacts | Dashboard tải dữ liệu | Mọi value xuất phát từ cùng run ID; không trộn artifacts giữa runs | Artifact-source test |
| AC-UI-004 | US-UI-003; PR-UI-010 | P0 | Backend metric artifact bị thay đổi có kiểm soát | Dashboard reload | UI phản ánh artifact; không có implementation tài chính riêng tạo số khác | Reconciliation test |
| AC-UI-005 | US-UI-003; PR-UI-011 | P1 | Metric hiển thị | User xem detail | Có label, unit, confidence level nếu áp dụng và run source | UI metadata checklist |
| AC-UI-006 | US-QNT-002; PR-UI-012 | P0 | Candidate table được sort/filter | User xem actions | Bit-to-ticker mapping không đổi | UI mapping regression |
| AC-UI-007 | US-UI-006; PR-UI-013 | P0 | Cached/offline run được mở | Dashboard hiển thị | Có nhãn offline/cached, data timestamp và không gọi real-time | UI capture |
| AC-UI-008 | US-UI-004; PR-UI-014 | P1 | Completed run | Export report được tạo | Report có portfolio input, dates, versions, methodology, assumptions, results, benchmark, warnings, limitations | Export checklist |
| AC-UI-009 | US-FIN-006; PR-UI-015 | P0 | Final actions tồn tại | Export/action table tạo | Mỗi row có ticker, old weight, bits, Quantum reduction, polished reduction, sell value, new weight | Table schema test |
| AC-UI-010 | US-QNT-008; PR-UI-016 | P0 | Run dùng fallback | Dashboard/report mở | Requested solver, actual solver và failure reason đều hiển thị; không gắn nhãn fallback là Quantum recommendation | Content review |
| AC-UI-011 | US-FIN-005; PR-UI-017 | P0 | Recommendation không cải thiện hoặc có critical warning | UI render | Warning đủ nổi bật bằng text và trạng thái, không chỉ màu sắc | UX review |
| AC-UI-012 | US-UI-005; PR-UI-018 | P0 | Final result hoặc report được xem | User tới recommendation | Disclaimer nêu decision-support, không tự đặt lệnh, không bảo đảm lợi nhuận và không thay thế tư vấn | UI/report review |

---

# 13. ACCEPTANCE CRITERIA — CONFIGURATION, AUDIT VÀ OPERATIONS

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-GOV-001 | US-GOV-001; PR-CFG-001–002 | P0 | Config baseline được đề xuất | Validation/phê duyệt chạy | Config có version, status, approver, effective date, change reason và hash | Config Registry |
| AC-GOV-002 | US-GOV-001; PR-CFG-003 | P0 | Approved config và source code | Config injection test chạy | Runtime values khớp config; không có conflicting hard-coded values ở critical functions | Config test, code scan |
| AC-GOV-003 | US-GOV-001; PR-CFG-004–006 | P0 | Development override được dùng | Run bắt đầu | Manifest ghi override và status `NON_BASELINE_RUN`; approved config không bị sửa | Run manifest |
| AC-GOV-004 | US-GOV-002; PR-CFG-007–010 | P0 | Completed run | Auditor tra registries | Data, model, financial policy và Quantum registry versions đều truy xuất được | Registry links |
| AC-GOV-005 | US-GOV-003; PR-CFG-011–013 | P0 | Thay đổi universe/action/risk metric/Quantum dimension | Team yêu cầu merge | Có approved Change Request, impact analysis và migration/test plan trước merge | Change Request |
| AC-GOV-006 | US-AUD-001; PR-AUD-001–002 | P0 | Run hoàn tất | Manifest validation chạy | `run_manifest.json` có versions của data, config, models, QUBO, solver, code và dashboard | Manifest schema test |
| AC-GOV-007 | US-AUD-001; PR-AUD-003–004 | P0 | Stochastic modules chạy | Artifact audit | Seed/seed list, producer, timestamp, schema version và run ID đầy đủ | Artifact audit report |
| AC-GOV-008 | US-AUD-001; PR-AUD-005–007 | P0 | Report/dashboard có metric | Truy xuất evidence | Mỗi metric tìm được artifact/script; environment lockfile tồn tại; không có số viết tay | Lineage audit |
| AC-GOV-009 | US-AUD-001; PR-AUD-008 | P0 | Same exact input/config/version | Exact path chạy lại | Deterministic outputs và QUBO/exact result hashes khớp | Reproduction report |
| AC-GOV-010 | US-AUD-001; PR-AUD-009–010 | P1 | Registered QAOA seeds/backend versions | Người khác chạy lại | Kết quả aggregate nằm trong tolerance; thành viên ngoài owner hoàn tất runbook | Reproduction/UAT evidence |
| AC-GOV-011 | US-AUD-002; PR-AUD-011–012 | P0 | Một claim trong report | RTM audit | Claim liên kết Scope/Story/Requirement/AC/Test/Evidence; thiếu link làm criterion fail | RTM export |
| AC-GOV-012 | US-OPS-001; PR-OPS-004–007 | P1 | Một module exception/timeout | Error handler chạy | Structured error có code, module, run ID, retry rule và recommended action; technical exception chỉ ở log | Error response/log |
| AC-GOV-013 | US-OPS-002; PR-OPS-001–003, PR-OPS-008 | P1 | Máy sạch theo supported environment | Thành viên làm theo runbook | Cài đặt, mở dashboard và tải cached validated run thành công | Installation/runbook record |
| AC-GOV-014 | US-GOV-004; GATE-10 | P0 | Tất cả module gates pass | Product Owner thực hiện UAT | End-to-end outcome, dashboard, export, disclaimer và limitations được ký chấp nhận; không còn P0 defect | UAT Report, sign-off |

---

# 14. ACCEPTANCE CRITERIA — NON-FUNCTIONAL

| ID | Trace | Mức | Given | When | Then | Evidence |
|---|---|---:|---|---|---|---|
| AC-NFR-001 | PR-NFR-COR-001–005 | P0 | Unit fixtures cho CVaR, cost, turnover, encode/decode, accounting | Test suite chạy | Toàn bộ critical numerical tests pass trong approved tolerances | Unit-test report |
| AC-NFR-002 | PR-NFR-COR-002 | P0 | Tolerance config thay đổi hợp lệ | Regression chạy | Tất cả comparisons dùng injected tolerance; không có arbitrary tolerance mới | Config/code test |
| AC-NFR-003 | PR-NFR-COR-003–004 | P0 | Interface nhận sai ticker order, unit, `NaN` hoặc `Inf` | Contract validation chạy | Input bị map đúng hoặc từ chối trước module calculation | Contract tests |
| AC-NFR-004 | PR-NFR-REL-001 | P0 | Critical module fail | Orchestrator kết thúc run | Không có output `COMPLETED`; final recommendation không tồn tại | Failure-state test |
| AC-NFR-005 | PR-NFR-REL-002–004 | P1 | Fallback/resume/rerun cases | Reliability tests chạy | Chỉ approved fallback dùng; artifacts ghi atomically/completion marker; không ghi đè run cũ | Reliability report |
| AC-NFR-006 | PR-NFR-REP-001 | P0 | Cùng deterministic inputs và versions | Chạy ít nhất hai lần | Outputs critical giống nhau theo exact equality/hash hoặc approved numerical rule | Reproducibility report |
| AC-NFR-007 | PR-NFR-REP-002–003 | P1 | Cùng stochastic config/seed/backend | Chạy lại | Outputs/aggregate metrics tái lập trong tolerance; checksums/manifests tồn tại | Reproduction artifacts |
| AC-NFR-008 | PR-NFR-PERF-001 | P1 | Cached validated run trên reference hardware | Thực hiện common UI actions | Response đáp ứng SLA đã pre-register; hardware và measurement method được ghi | Performance report |
| AC-NFR-009 | PR-NFR-PERF-002 | P0 | User chỉ sort/filter UI | Interaction xảy ra | Không có QAOA/exact/scenario job mới được khởi chạy | Backend call log |
| AC-NFR-010 | PR-NFR-PERF-003–005 | P1 | Exact 20-bit, 2.000/5.000 scenarios và dev solver modes | Benchmark chạy | Runtime/memory nằm trong budget đã khóa hoặc có approved fallback; dev output gắn `NON_FINAL_CONFIG` | Benchmark report |
| AC-NFR-011 | PR-NFR-SEC-001–005 | P0 | Security scan và runtime | Scan/test chạy | Không PII bắt buộc, không secrets trong repo/log, upload được kiểm tra, không broker endpoint/credential | Security checklist |
| AC-NFR-012 | PR-NFR-UX-001–003 | P1 | Dashboard có metrics và errors | UX review | Metric có unit/giải thích; lỗi có hướng xử lý; màu không là tín hiệu duy nhất | UX checklist |
| AC-NFR-013 | PR-NFR-UX-004–005 | P0 | Final output hiển thị | UX review | Raw/polished tách biệt và disclaimer xuất hiện tại recommendation | UI evidence |
| AC-NFR-014 | PR-NFR-EXP-001–003 | P1 | Regime, candidate và final actions tồn tại | Explainability review | State profile, score components và bit→action→polishing lineage đều truy xuất được | Explainability report |
| AC-NFR-015 | PR-NFR-EXP-004–005 | P0 | Technical report/dashboard content | Product review | Có survivorship/model/scenario/QUBO limitations; không diễn giải correlation thành causality | Content checklist |
| AC-NFR-016 | PR-NFR-MNT-001–003 | P1 | Source tree và schemas | Architecture review | Data/AI/Risk/Quantum/UI tách module; schemas versioned; migration/regression có cho breaking change | Architecture review |
| AC-NFR-017 | PR-NFR-MNT-004–005 | P0 | Critical logic được kiểm tra | Code review | Core logic tồn tại trong shared modules, không chỉ notebook; notebooks gọi shared implementations | Code-review evidence |
| AC-NFR-018 | PR-NFR-EXP-004; Product Scope | P0 | Quantum benchmark được công bố | Report review | Không có claim quantum advantage, guaranteed profit hoặc guaranteed loss prevention khi chưa có evidence | Claims review |

---

# 15. END-TO-END ACCEPTANCE SCENARIOS

## E2E-AC-001 — Happy path final run

**Trace:** Toàn bộ core journey; P0.

```gherkin
Given một approved universe, approved config và danh mục có ít nhất 10 held-eligible positions
And dữ liệu, HMM và scenario quality gates đều pass
When người dùng chạy Q-SHIELD ở Final mode
Then hệ thống sinh 5.000 scenarios với horizon 20 ngày
And tính baseline CVaR 95%, 97,5% và 99%
And chọn đúng top 10 và lưu candidate order
And xây QUBO 20-bit đã validation
And chạy exact reference và Warm-start QAOA
And tính lại true financial objective cho candidate pool
And polishing giữ nguyên zero-action active-set lock
And final portfolio pass accounting constraints
And dashboard/report khớp artifacts của cùng run
And run kết thúc ở trạng thái COMPLETED
```

## E2E-AC-002 — Temporal leakage blocker

```gherkin
Given dataset chứa thông tin sau evaluation date trong một feature
When Data Gate chạy
Then hệ thống phát hiện temporal leakage
And run chuyển sang FAILED_DATA
And HMM, Scenario, QUBO và final recommendation không được tạo
```

## E2E-AC-003 — Surrogate validation blocker

```gherkin
Given objective samples hợp lệ nhưng QUBO surrogate không đạt ranking threshold
When QUBO Gate chạy
Then hệ thống phát hành ERR_QUBO_SURROGATE_VALIDATION
And không chạy QAOA như một valid baseline run
And dashboard không hiển thị Quantum recommendation
```

## E2E-AC-004 — QAOA fallback

```gherkin
Given tất cả gates trước Solver Gate đã pass
And QAOA backend timeout
When fallback policy được áp dụng
Then exact hoặc classical solver đã phê duyệt được dùng
And run có trạng thái COMPLETED_WITH_FALLBACK
And requested_solver, actual_solver và reason được hiển thị
And output không được gắn nhãn Quantum recommendation
```

## E2E-AC-005 — Accounting blocker

```gherkin
Given một solver candidate dẫn đến accounting inconsistency
When Finance Gate chạy
Then hệ thống phát hành ERR_FIN_ACCOUNTING
And candidate không được chọn làm final recommendation
And nếu không còn candidate hợp lệ thì run không được COMPLETED
```

## E2E-AC-006 — Dashboard artifact reconciliation

```gherkin
Given một completed run có immutable artifacts
When dashboard và exported report được tạo
Then tất cả metrics khớp artifacts trong tolerance
And tất cả outputs có cùng run ID
And không có số liệu viết tay hoặc financial calculation riêng ở UI
```

---

# 16. QUALITY-GATE ACCEPTANCE MATRIX

| Gate | Acceptance Criteria chính | Owner | Pass condition |
|---|---|---|---|
| GATE-01 Scope/Config | AC-GOV-001–005 | NGOC/TÂN | Scope/config approved; không conflicting values |
| GATE-02 Data | AC-DAT-001–014 | MINHANH | Schema, quality, temporal integrity, eligibility pass |
| GATE-03 Regime | AC-REG-001–011 | TÚ | Model selected có căn cứ; probabilities hợp lệ |
| GATE-04 Scenario | AC-SCN-001–012 | TÚ/PHÚC | Cube đúng và validation pass |
| GATE-05 Risk | AC-RSK-001–015 | PHÚC | CVaR/cost/objective đúng |
| GATE-06 Candidate | AC-CAN-001–012 | PHÚC | Top 10 deterministic, coverage/policy hợp lệ |
| GATE-07 QUBO | AC-QUB-001–015 | TÂN/PHÚC | Mapping, samples, surrogate và hash pass |
| GATE-08 Solver | AC-SLV-001–013 | TÂN | Exact/QAOA/classical benchmark hợp lệ |
| GATE-09 Finance | AC-FIN-001–015 | PHÚC/TÂN | True re-ranking, polishing và accounting pass |
| GATE-10 Product | AC-UI-001–012, AC-GOV-014, AC-NFR-* | NGOC | UI reconciliation, UAT, claims và disclaimer pass |

---

# 17. TRACEABILITY SUMMARY

| User Story group | Acceptance Criteria range | Requirement range |
|---|---|---|
| US-RUN-* | AC-RUN-001–012 | PR-RUN-001–012 |
| US-DAT-* | AC-DAT-001–014 | PR-DAT-001–020 |
| US-REG-* | AC-REG-001–012 | PR-REG-001–015 |
| US-SCN-* | AC-SCN-001–012 | PR-SCN-001–015 |
| US-RSK-* | AC-RSK-001–015 | PR-RSK-001–020 |
| US-CAN-* | AC-CAN-001–012 | PR-CAN-001–015 |
| US-QNT-* | AC-QUB-001–015, AC-SLV-001–013 | PR-QUB-001–017, PR-SLV-001–015 |
| US-FIN-* | AC-FIN-001–015 | PR-FIN-001–018 |
| US-UI-* | AC-UI-001–012 | PR-UI-001–018 |
| US-GOV/AUD/OPS-* | AC-GOV-001–014 | PR-CFG, PR-AUD, PR-OPS |
| Cross-cutting | AC-NFR-001–018 | PR-NFR-* |

---

# 18. DEFINITION OF ACCEPTED

Một User Story chỉ được chuyển sang `ACCEPTED` khi:

1. Tất cả Acceptance Criteria P0/P1 liên quan ở trạng thái PASS hoặc P1 được defer có phê duyệt.
2. Không có defect P0 đang mở.
3. Test evidence có run ID, config/data/model versions và reviewer.
4. Negative, boundary và fallback cases liên quan đã được chạy.
5. RTM cập nhật Story → Requirement → AC → Test → Evidence.
6. Dashboard/report nếu liên quan khớp backend artifacts.
7. Owner module và reviewer ngoài module owner xác nhận.
8. Product Owner chấp thuận đối với story có tác động người dùng hoặc claim sản phẩm.

---

# 19. MACHINE-READABLE ACCEPTANCE SUMMARY

```yaml
document: QSHIELD-AC-001
version: 1.0
status: baseline_candidate
parents:
  scope: QSHIELD-PSS-001-v1.0
  requirements: QSHIELD-PRS-001-v1.0
  user_stories: QSHIELD-US-001-v1.0

acceptance_groups:
  RUN: AC-RUN-001/AC-RUN-012
  DAT: AC-DAT-001/AC-DAT-014
  REG: AC-REG-001/AC-REG-012
  SCN: AC-SCN-001/AC-SCN-012
  RSK: AC-RSK-001/AC-RSK-015
  CAN: AC-CAN-001/AC-CAN-012
  QUB: AC-QUB-001/AC-QUB-015
  SLV: AC-SLV-001/AC-SLV-013
  FIN: AC-FIN-001/AC-FIN-015
  UI: AC-UI-001/AC-UI-012
  GOV: AC-GOV-001/AC-GOV-014
  NFR: AC-NFR-001/AC-NFR-018

release_blocking_principles:
  - no_future_data_leakage
  - no_invalid_scenario_cube
  - canonical_financial_objective_only
  - deterministic_candidate_order
  - validated_qubo_before_qaoa
  - same_qubo_hash_across_solvers
  - no_seed_cherry_picking
  - true_objective_reranking_required
  - quantum_zero_action_locked_during_polishing
  - portfolio_accounting_must_reconcile
  - dashboard_must_match_artifacts
  - no_automatic_trading
  - no_quantum_advantage_claim_without_evidence

result_states:
  - NOT_RUN
  - PASS
  - FAIL
  - BLOCKED
  - DEFERRED
  - NOT_APPLICABLE
```

---

# 20. PHÊ DUYỆT

| Vai trò | Họ tên | Trạng thái | Ngày |
|---|---|---|---|
| Product Owner | Nguyễn Thị Ánh Ngọc | Chờ phê duyệt | TBD |
| QA/Quant Risk Owner | Liêu Hoài Phúc | Chờ xác nhận | TBD |
| Data Owner | Nguyễn Đỗ Minh Anh | Chờ xác nhận | TBD |
| AI/ML Owner | Nguyễn Anh Tú | Chờ xác nhận | TBD |
| Technical/Quantum Owner | Đỗ Ngọc Tân | Chờ xác nhận | TBD |

---

**Kết thúc tài liệu — QSHIELD-AC-001 v1.0 Baseline Candidate**
