---
document_id: QSHIELD-PRS-001
document_title: Q-SHIELD Product Requirements Specification
document_version: 1.0
document_status: Baseline Candidate
product_name: Q-SHIELD
team_name: NOVARIS
parent_scope_document: QSHIELD-PSS-001
parent_scope_version: 1.0
requirements_owner: Nguyễn Thị Ánh Ngọc
technical_owner: Đỗ Ngọc Tân
reviewers:
  - Nguyễn Đỗ Minh Anh
  - Nguyễn Anh Tú
  - Liêu Hoài Phúc
language: vi-VN
last_updated: 2026-08-02
---

# Q-SHIELD — PRODUCT REQUIREMENTS SPECIFICATION

## Đặc tả yêu cầu sản phẩm cho hệ thống Quantum–AI hỗ trợ quản trị tail risk danh mục cổ phiếu

**Đội dự án:** NOVARIS
**Product Owner:** Nguyễn Thị Ánh Ngọc
**Tài liệu phạm vi cha:** `QSHIELD-PSS-001 v1.0`
**Trạng thái:** Baseline Candidate
**Mục đích:** Chuyển Product Scope thành các yêu cầu có thể thiết kế, lập trình, tích hợp, kiểm thử và truy xuất bằng evidence.

---

# 1. MỤC ĐÍCH VÀ PHẠM VI TÀI LIỆU

## 1.1. Mục đích

Tài liệu này xác định đầy đủ các yêu cầu sản phẩm của Q-SHIELD ở mức có thể bàn giao cho đội dữ liệu, AI/ML, Quant Risk, Quantum/Software và QA. Mỗi yêu cầu được viết theo nguyên tắc:

- Có một hành vi hoặc kết quả cần đạt.
- Có owner và mức ưu tiên.
- Có nguồn gốc từ Product Scope.
- Có đầu vào, đầu ra hoặc quy tắc kiểm chứng.
- Có thể liên kết sang Acceptance Criteria và Test Case.
- Không phụ thuộc vào cách trình bày riêng của dashboard.

## 1.2. Ranh giới tài liệu

Product Requirements Specification trả lời câu hỏi **“sản phẩm phải làm gì và phải đáp ứng điều kiện nào”**. Tài liệu không thay thế:

- Data Contract: schema và quy tắc chi tiết của từng bảng/artifact.
- Model Specification: feature, training procedure và hyperparameter chi tiết.
- Financial Objective Specification: công thức, scale và calibration chi tiết.
- QUBO Design Specification: phép biến đổi toán học và circuit implementation.
- Acceptance Criteria/Test Plan: dữ liệu test, bước chạy và expected result cụ thể.
- Config Registry: giá trị tham số đã phê duyệt cho từng release.

## 1.3. Quan hệ giữa các tài liệu

```text
Product Scope Statement
        ↓
Product Requirements Specification
        ↓
User Stories + Acceptance Criteria
        ↓
Data/Model/Financial/QUBO/Interface Specifications
        ↓
Source Code + Test Cases + Run Artifacts
        ↓
UAT Report + Technical Report + Dashboard
```

Không được dùng source code, dashboard hoặc slide để âm thầm thay đổi requirement đã được phê duyệt.

---

# 2. QUY ƯỚC ĐẶC TẢ

## 2.1. Từ khóa chuẩn

| Từ khóa | Ý nghĩa |
|---|---|
| **PHẢI / SHALL** | Bắt buộc để release; không đạt thì requirement fail |
| **NÊN / SHOULD** | Quan trọng nhưng có thể defer nếu Product Owner chấp thuận và ghi limitation |
| **CÓ THỂ / MAY** | Tùy chọn; không phải điều kiện nghiệm thu core release |
| **KHÔNG ĐƯỢC / SHALL NOT** | Hành vi bị cấm |

## 2.2. Mức ưu tiên

| Priority | Định nghĩa |
|---|---|
| P0 — Critical | Thiếu hoặc sai sẽ làm kết quả tài chính/Quantum không hợp lệ; chặn release |
| P1 — Must Have | Bắt buộc cho core product và UAT |
| P2 — Should Have | Có giá trị lớn nhưng có thể defer có kiểm soát |
| P3 — Could Have | Enhancement; không chặn release |

## 2.3. Trạng thái requirement

| Trạng thái | Ý nghĩa |
|---|---|
| Draft | Đang soạn |
| Baseline Candidate | Đã đủ nội dung nhưng còn phụ thuộc quyết định/config mở |
| Approved | Được Product Owner và owner liên quan phê duyệt |
| Implemented | Có implementation và unit/integration evidence |
| Verified | Acceptance Criteria và Test Case pass |
| Deferred | Có quyết định hoãn và lý do |
| Deprecated | Không còn dùng; có migration note |

## 2.4. Cấu trúc mã yêu cầu

`PR-<DOMAIN>-<NUMBER>`

| Domain | Nội dung |
|---|---|
| RUN | Run lifecycle và portfolio intake |
| DAT | Dữ liệu, universe và eligibility |
| REG | Market regime/HMM |
| SCN | Scenario generation |
| RSK | Risk Engine và financial metrics |
| CAN | Candidate selection và stress policy |
| QUB | Objective sampling và QUBO surrogate |
| SLV | Exact, classical và QAOA solver |
| FIN | Re-ranking, polishing và portfolio accounting |
| UI | Dashboard, report và user interaction |
| CFG | Configuration và model/data registry |
| AUD | Audit, evidence và reproducibility |
| OPS | Deployment, fallback và run operation |
| NFR | Yêu cầu phi chức năng |

## 2.5. Owner shorthand

| Mã | Thành viên |
|---|---|
| NGOC | Nguyễn Thị Ánh Ngọc |
| MINHANH | Nguyễn Đỗ Minh Anh |
| TÚ | Nguyễn Anh Tú |
| PHÚC | Liêu Hoài Phúc |
| TÂN | Đỗ Ngọc Tân |

---

# 3. PRODUCT BASELINE

## 3.1. Baseline nghiệp vụ

| Thuộc tính | Baseline |
|---|---|
| Product type | Decision-support system; không phải trading execution system |
| Primary user | Người quản lý danh mục cổ phiếu thuộc universe đã chốt, không dùng phái sinh |
| Universe | Fixed snapshot 30 mã VN30; eligibility và top 10 thay đổi theo evaluation date |
| Data frequency | Daily |
| Market-level train | 2016–2022 |
| Asset-level train | 02/07/2018–2022 |
| Validation | 2023 |
| Test | 2024–30/06/2026 |
| Regime model | Gaussian HMM; thử 2–5 states |
| Scenario champion | Regime-conditioned moving-block bootstrap |
| Scenario challenger | Conditional VAE |
| Scenario count | 2.000 development; 5.000 final |
| Horizon | 20 trading days |
| Primary risk metric | CVaR 95% |
| Robustness metrics | CVaR 97,5% và 99% |
| Quantum candidates | Dynamic top 10 |
| Action levels | Giảm 0%, 10%, 20%, 30% vị thế hiện tại |
| Encoding | 2 bits/asset; 20 bits |
| Reference | Exact evaluation trên `2^20` QUBO states |
| Quantum solver | Warm-start QAOA p=1; p=2 challenger |
| Post-Quantum | True-objective re-ranking và bounded local polishing |
| Hedge instrument | Cash only |
| Interface | Streamlit dashboard + exported artifacts |

## 3.2. Product invariants

Các invariant sau không được thay đổi bằng config thông thường:

1. Không dùng dữ liệu sau evaluation date.
2. Không short selling, không leverage, không phái sinh và không mua tăng trong R1.
3. Action thể hiện tỷ lệ giảm của vị thế hiện tại.
4. Quantum quyết định active set và coarse sizing.
5. Quantum action 0% không được polishing kích hoạt.
6. Final recommendation phải được tính lại bằng true financial objective.
7. Dashboard chỉ đọc artifacts, không có financial logic độc lập.
8. Không phát hành kết quả lỗi dưới trạng thái thành công.
9. Không tuyên bố quantum advantage nếu chưa có bằng chứng.

---

# 4. ACTORS VÀ QUYỀN HẠN

| Actor ID | Actor | Quyền trong R1 | Không có quyền |
|---|---|---|---|
| ACT-001 | Portfolio User | Nhập danh mục, chạy phân tích, xem và export kết quả | Gửi lệnh giao dịch, sửa config approved |
| ACT-002 | Product Owner | Phê duyệt scope, config nghiệp vụ, UAT và nội dung công bố | Sửa artifact của model run sau khi hoàn tất |
| ACT-003 | Model/Risk Validator | Xem validation, benchmark, artifacts và test evidence | Thay đổi model/config mà không tạo version |
| ACT-004 | System Administrator | Quản lý version, cache, run, deployment và logs | Thay đổi policy tài chính không có phê duyệt |
| ACT-005 | Judge/Reviewer | Xem demo, report, assumptions, benchmark và limitations | Thực hiện giao dịch hoặc thay đổi hệ thống |

---

# 5. RUN LIFECYCLE VÀ PORTFOLIO INTAKE REQUIREMENTS

## 5.1. Run state machine

```text
CREATED
  → VALIDATING
  → DATA_READY
  → REGIME_READY
  → SCENARIOS_READY
  → RISK_READY
  → CANDIDATES_READY
  → QUBO_READY
  → SOLVED
  → RERANKED
  → POLISHED
  → COMPLETED
```

Mỗi bước có thể chuyển sang `FAILED_<MODULE>` hoặc `COMPLETED_WITH_FALLBACK` theo quy tắc đã định.

## 5.2. Danh mục yêu cầu

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-RUN-001 | Hệ thống PHẢI nhận evaluation date, ticker, position value hoặc weight, cash ban đầu và run mode | P0 | NGOC/TÂN | FUNC-001, IN-001–005 |
| PR-RUN-002 | Hệ thống PHẢI hỗ trợ một và chỉ một đơn vị nội bộ cho tỷ trọng: decimal trong `[0,1]`; UI có thể hiển thị `%` | P0 | TÂN/PHÚC | BR-017 |
| PR-RUN-003 | Mỗi request hợp lệ PHẢI được gán `run_id` duy nhất trước khi module tính toán đầu tiên chạy | P0 | TÂN | FUNC-003 |
| PR-RUN-004 | Hệ thống PHẢI lưu bản sao bất biến của portfolio input theo `run_id` | P0 | TÂN | FUNC-078 |
| PR-RUN-005 | Hệ thống PHẢI từ chối ticker trùng, value/weight âm, cash âm, ngày sai định dạng và tổng tỷ trọng sai tolerance | P0 | TÂN/MINHANH | FUNC-002 |
| PR-RUN-006 | Hệ thống KHÔNG ĐƯỢC tự sửa input, tự loại ticker hoặc tự normalize weights mà không trả warning và nhận xác nhận theo policy | P0 | NGOC/TÂN | FUNC-004 |
| PR-RUN-007 | Run PHẢI lưu `requested_solver`, `actual_solver`, `requested_scenario_count` và `actual_scenario_count` | P1 | TÂN | FUNC-054, FUNC-078 |
| PR-RUN-008 | Mỗi state transition PHẢI có timestamp, producer module và status message | P1 | TÂN | NFR-006–008 |
| PR-RUN-009 | Hệ thống PHẢI ngăn chỉnh sửa artifacts của run đã `COMPLETED`; chạy lại phải tạo run mới | P0 | TÂN | FUNC-078–081 |
| PR-RUN-010 | Nếu có dưới 10 vị thế dương và eligible, hệ thống PHẢI trả risk analysis nhưng KHÔNG ĐƯỢC phát hành 20-bit Quantum recommendation | P0 | NGOC/TÂN | FUNC-005 |
| PR-RUN-011 | Run lỗi PHẢI giữ nguyên artifacts đã sinh trước lỗi để phục vụ debug, nhưng không được xuất final recommendation | P1 | TÂN | BR-020 |
| PR-RUN-012 | Người dùng PHẢI thấy rõ run đang chạy, hoàn tất, fallback hay thất bại | P1 | TÂN | FUNC-069 |

## 5.3. Quy tắc tổng tỷ trọng

Nếu input theo weight:

\[
\left|\sum_i w_i+w_{cash}-1\right|\le\epsilon_w.
\]

`epsilon_w` phải nằm trong Config Registry. Nếu input theo position value, hệ thống chuẩn hóa bằng tổng NAV và lưu cả value gốc lẫn weight dẫn xuất.

---

# 6. DATA, UNIVERSE VÀ ELIGIBILITY REQUIREMENTS

## 6.1. Universe Registry

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-DAT-001 | Hệ thống PHẢI sử dụng Universe Registry có đúng 30 ticker, snapshot date, nguồn, version và approval status | P0 | MINHANH | DATA-001–003 |
| PR-DAT-002 | Danh sách 30 ticker của một approved release PHẢI bất biến; thay đổi phải tạo universe version mới | P0 | MINHANH/NGOC | BR-001 |
| PR-DAT-003 | Mỗi run PHẢI lưu universe version thực tế được dùng | P0 | MINHANH/TÂN | OUT-TECH-003 |
| PR-DAT-004 | Báo cáo PHẢI công bố universe là fixed snapshot và có survivorship-bias limitation | P0 | NGOC | FUNC-010, RSK-001 |

## 6.2. Nguồn và schema dữ liệu

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-DAT-005 | Mỗi record giá PHẢI có `date`, `ticker`, `adjusted_close`, `volume`, `source_id`, `data_version` | P0 | MINHANH | DATA-004–006 |
| PR-DAT-006 | `date+ticker` PHẢI là unique key trong bảng giá chuẩn hóa | P0 | MINHANH | DATA-015 |
| PR-DAT-007 | Hệ thống PHẢI kiểm tra type, null, duplicate, non-positive price, negative volume và calendar consistency | P0 | MINHANH | FUNC-007, DATA-015 |
| PR-DAT-008 | Corporate actions PHẢI được xử lý qua adjusted price hoặc adjustment procedure có evidence | P0 | MINHANH | DATA-014 |
| PR-DAT-009 | Source Registry PHẢI lưu nguồn, quyền sử dụng, acquisition method, refresh date và fallback source | P1 | MINHANH/NGOC | DEP-002 |
| PR-DAT-010 | Credentials KHÔNG ĐƯỢC xuất hiện trong code, notebook, logs hoặc artifact | P0 | MINHANH/TÂN | NFR-019 |

## 6.3. Temporal integrity

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-DAT-011 | Feature tại ngày `t` chỉ PHẢI sử dụng dữ liệu có timestamp `≤t` | P0 | MINHANH | BR-003 |
| PR-DAT-012 | Hệ thống KHÔNG ĐƯỢC dùng centered rolling window hoặc backfill từ tương lai | P0 | MINHANH | DATA-009–010 |
| PR-DAT-013 | Train, validation và test boundaries PHẢI được kiểm tra tự động trước mỗi model run | P0 | MINHANH/TÚ | DATA-007–010 |
| PR-DAT-014 | Test data KHÔNG ĐƯỢC tham gia feature selection, model selection, threshold calibration hoặc objective-weight calibration | P0 | TÚ/PHÚC | BR-003, CON-008 |

## 6.4. Eligibility

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-DAT-015 | Eligibility PHẢI được tính lại tại từng evaluation date | P0 | MINHANH | FUNC-007 |
| PR-DAT-016 | Một ticker chỉ eligible khi đạt minimum history, minimum coverage, listing status và liquidity rule đã phê duyệt | P0 | MINHANH/PHÚC | DATA-011–013 |
| PR-DAT-017 | Hệ thống KHÔNG ĐƯỢC nội suy dữ liệu trước niêm yết hoặc giả định ticker tồn tại trước ngày giao dịch đầu tiên | P0 | MINHANH | BR-002 |
| PR-DAT-018 | Mỗi ticker bị loại PHẢI có machine-readable reason code | P1 | MINHANH | FUNC-009 |
| PR-DAT-019 | Chỉ ticker có position weight `>0` và eligible mới được đưa vào candidate pool | P0 | MINHANH/PHÚC | FUNC-008, BR-005 |
| PR-DAT-020 | Eligibility report PHẢI chứa universe count, eligible count, held-eligible count và excluded-by-reason counts | P1 | MINHANH | OUT-TECH-003 |

## 6.5. Error codes dữ liệu

| Error code | Điều kiện |
|---|---|
| `ERR_DATA_SCHEMA` | Thiếu hoặc sai field/type bắt buộc |
| `ERR_DATA_DUPLICATE_KEY` | Trùng `date+ticker` |
| `ERR_DATA_TEMPORAL_LEAKAGE` | Phát hiện dữ liệu tương lai |
| `ERR_DATA_UNIVERSE_VERSION` | Universe chưa approved hoặc không tồn tại |
| `ERR_DATA_INSUFFICIENT_HISTORY` | Không đủ lịch sử tối thiểu |
| `ERR_DATA_LOW_COVERAGE` | Coverage thấp hơn config |
| `ERR_DATA_NO_ELIGIBLE_POSITIONS` | Không còn vị thế hợp lệ để phân tích |

---

# 7. MARKET REGIME/HMM REQUIREMENTS

## 7.1. Training và model selection

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-REG-001 | Market Regime Engine PHẢI sử dụng market-level train 2016–2022 cho baseline | P0 | TÚ | FUNC-011, DATA-007 |
| PR-REG-002 | Engine PHẢI thử số state `[2,3,4,5]` và covariance candidates trong Config Registry | P0 | TÚ | FUNC-012 |
| PR-REG-003 | Mỗi candidate PHẢI được chạy trên danh sách seed đã đăng ký | P0 | TÚ | FUNC-012 |
| PR-REG-004 | Candidate report PHẢI có log-likelihood, AIC, BIC, convergence, state occupancy và stability | P0 | TÚ | FUNC-012 |
| PR-REG-005 | Số state KHÔNG ĐƯỢC chọn chỉ vì AIC/BIC thấp nhất; quyết định phải có stability và interpretability evidence | P0 | TÚ/PHÚC | FUNC-013 |
| PR-REG-006 | Ba state chỉ là expected configuration; model selection PHẢI có quyền chọn 2, 4 hoặc 5 nếu evidence tốt hơn | P1 | TÚ | FUNC-013 |
| PR-REG-007 | Validation 2023 PHẢI được dùng để đánh giá độ ổn định ngoài train nhưng không được trộn vào train khi so sánh baseline | P0 | TÚ | DATA-009 |

## 7.2. State semantics và inference

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-REG-008 | Mỗi state PHẢI được mô tả bằng return, volatility, drawdown và các feature profile liên quan | P1 | TÚ/PHÚC | FUNC-014 |
| PR-REG-009 | Label kinh tế `normal/volatile/stress` PHẢI được gắn sau khi fit dựa trên state profile, không dựa trên index state tùy ý | P0 | TÚ | FUNC-014 |
| PR-REG-010 | State probabilities tại mỗi ngày PHẢI nằm trong `[0,1]` và tổng bằng 1 trong tolerance | P0 | TÚ | FUNC-014 |
| PR-REG-011 | `p_stress` PHẢI là probability của state được phê duyệt là stress, không phải hard label 0/1 | P0 | TÚ | FUNC-014, FUNC-033 |
| PR-REG-012 | Inference tại evaluation date PHẢI chỉ dùng observations có sẵn đến ngày đó | P0 | TÚ | BR-003 |
| PR-REG-013 | Output PHẢI có model version, feature version, selected state, probabilities và uncertainty flags | P0 | TÚ | OUT-TECH-004 |
| PR-REG-014 | HMM không hội tụ PHẢI kích hoạt cấu hình fallback đã đăng ký và log reason | P1 | TÚ/TÂN | RSK-003 |
| PR-REG-015 | Không có model hợp lệ PHẢI chặn scenario conditioning và final recommendation | P0 | TÚ | BR-020 |

---

# 8. SCENARIO ENGINE REQUIREMENTS

## 8.1. Scenario generation

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-SCN-001 | Champion PHẢI là regime-conditioned moving-block bootstrap | P0 | TÚ | FUNC-016 |
| PR-SCN-002 | Development mode PHẢI hỗ trợ 2.000 paths; Final mode PHẢI hỗ trợ 5.000 paths | P0 | TÚ | FUNC-018 |
| PR-SCN-003 | Mỗi path PHẢI dài đúng 20 trading days | P0 | TÚ | FUNC-018 |
| PR-SCN-004 | Scenario cube PHẢI có dimension `[scenario, horizon, asset]` và ticker order được lưu riêng | P0 | TÚ | FUNC-018, OUT-TECH-005 |
| PR-SCN-005 | Bootstrap block PHẢI được lấy từ regime-consistent observations theo policy đã phê duyệt | P0 | TÚ | FUNC-019 |
| PR-SCN-006 | Block length PHẢI được chọn trên validation từ candidate set trong Config Registry | P1 | TÚ | FUNC-019 |
| PR-SCN-007 | Random seed PHẢI được đăng ký và lưu trong scenario manifest | P0 | TÚ | FUNC-021 |
| PR-SCN-008 | Scenario Engine PHẢI giữ cùng ticker order với Risk Engine hoặc cung cấp explicit mapping | P0 | TÚ/PHÚC | FUNC-021 |

## 8.2. Scenario validation

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-SCN-009 | Scenario cube KHÔNG ĐƯỢC chứa `NaN`, `Inf` hoặc sai shape | P0 | TÚ | FUNC-020 |
| PR-SCN-010 | Validation PHẢI so sánh moments, volatility, autocorrelation, cross-asset correlation và tail quantiles | P0 | TÚ/PHÚC | FUNC-020 |
| PR-SCN-011 | Validation PHẢI kiểm tra stress-conditioned scenarios có profile rủi ro hợp lý hơn normal-conditioned scenarios | P1 | TÚ/PHÚC | FUNC-020 |
| PR-SCN-012 | Mỗi validation metric PHẢI có threshold hoặc interpretation rule trong Config Registry/Model Specification | P0 | TÚ | FUNC-020 |
| PR-SCN-013 | Scenario quality gate fail PHẢI chặn Risk Engine hoặc chuyển sang approved fallback model | P0 | TÚ/TÂN | BR-020 |
| PR-SCN-014 | Conditional VAE CÓ THỂ chạy như challenger; thất bại của CVAE KHÔNG ĐƯỢC làm hỏng champion pipeline | P2 | TÚ | FUNC-017 |
| PR-SCN-015 | Challenger chỉ được thay champion khi có validation evidence và Decision Log approval | P1 | TÚ/NGOC | FUNC-017 |

---

# 9. RISK ENGINE REQUIREMENTS

## 9.1. Return, loss và baseline metrics

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-RSK-001 | Risk Engine PHẢI dùng một sign convention duy nhất: `loss = -portfolio_return` | P0 | PHÚC | FUNC-022 |
| PR-RSK-002 | Portfolio scenario return PHẢI sử dụng cùng weights, ticker order và scenario paths của run | P0 | PHÚC | FUNC-022 |
| PR-RSK-003 | Engine PHẢI tính VaR và CVaR tại 95%, 97,5% và 99% | P0 | PHÚC | FUNC-023 |
| PR-RSK-004 | CVaR 95% PHẢI là objective chính; 97,5% và 99% chỉ là robustness outputs | P0 | PHÚC | BR-004 |
| PR-RSK-005 | Engine PHẢI tính expected return, maximum drawdown và các metric trước–sau đã phê duyệt | P1 | PHÚC | FUNC-025 |
| PR-RSK-006 | CVaR implementation PHẢI có unit test trên synthetic loss arrays có expected value xác định | P0 | PHÚC | NFR-001 |
| PR-RSK-007 | Engine PHẢI báo số tail observations được dùng cho mỗi confidence level | P1 | PHÚC | FUNC-024 |
| PR-RSK-008 | CVaR 99% PHẢI đi kèm confidence interval và stability warning khi tail sample thấp | P0 | PHÚC | FUNC-024 |

## 9.2. Cost, turnover và liquidity

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-RSK-009 | Transaction cost PHẢI gồm các thành phần được Config Registry phê duyệt và trả breakdown | P0 | PHÚC | FUNC-025 |
| PR-RSK-010 | Cost rate, sell tax và slippage KHÔNG ĐƯỢC hard-code trong hàm tính | P0 | PHÚC/TÂN | TBD-002 |
| PR-RSK-011 | Turnover PHẢI có một định nghĩa duy nhất và cùng unit trong sampling, re-ranking, dashboard | P0 | PHÚC | FUNC-027 |
| PR-RSK-012 | Liquidity penalty PHẢI dùng proxy có nguồn, scale và direction rõ ràng | P1 | PHÚC/MINHANH | FUNC-025 |
| PR-RSK-013 | Sensitivity analysis PHẢI đánh giá ít nhất base, low-cost và high-cost assumptions trong final report | P1 | PHÚC | RSK-007 |

## 9.3. Financial objective

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-RSK-014 | Hệ thống PHẢI có một canonical `financial_objective()` được Risk Engine sở hữu | P0 | PHÚC | FUNC-027, DEP-005 |
| PR-RSK-015 | Objective PHẢI gồm CVaR, return sacrifice, cost, turnover, liquidity và cash-budget deviation theo approved config | P0 | PHÚC | FUNC-042 |
| PR-RSK-016 | Mỗi objective component PHẢI có raw value, scaled value, weight và weighted contribution | P0 | PHÚC | FUNC-043 |
| PR-RSK-017 | Scaling parameters PHẢI được fit trên train/validation và khóa trước test | P0 | PHÚC | FUNC-043 |
| PR-RSK-018 | Thay đổi objective weight PHẢI tạo config version mới và không ghi đè run cũ | P0 | PHÚC/NGOC | NFR-008 |
| PR-RSK-019 | Objective PHẢI trả constraint violations riêng, không che chúng trong scalar score | P0 | PHÚC/TÂN | FUNC-047 |
| PR-RSK-020 | Risk result PHẢI lưu metric definitions, units, confidence levels và config hash | P1 | PHÚC | OUT-TECH-006 |

---

# 10. CANDIDATE SELECTION VÀ STRESS POLICY REQUIREMENTS

## 10.1. Candidate score

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-CAN-001 | Engine PHẢI tính marginal CVaR reduction cho mỗi held-eligible asset theo cùng baseline scenarios | P0 | PHÚC | FUNC-026 |
| PR-CAN-002 | Candidate score PHẢI kết hợp marginal risk reduction, transaction cost và illiquidity penalty | P0 | PHÚC | FUNC-029 |
| PR-CAN-003 | Score components PHẢI được lưu riêng để giải thích | P1 | PHÚC | FUNC-072 |
| PR-CAN-004 | Score weights PHẢI nằm trong Config Registry và khóa trước test | P0 | PHÚC/NGOC | TBD-003 |
| PR-CAN-005 | Engine PHẢI chọn đúng 10 ứng viên khi có ít nhất 10 held-eligible assets | P0 | PHÚC | FUNC-028 |
| PR-CAN-006 | Candidate order PHẢI deterministic với cùng data/config | P0 | PHÚC | FUNC-030 |
| PR-CAN-007 | Tie-break PHẢI theo approved sequence và lưu reason khi được áp dụng | P1 | PHÚC | FUNC-030 |
| PR-CAN-008 | `candidate_order.json` PHẢI chứa rank, ticker, score và source portfolio weight | P0 | PHÚC/TÂN | OUT-TECH-007 |

## 10.2. Coverage và sensitivity

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-CAN-009 | Engine PHẢI tính top-10 risk coverage theo công thức được phê duyệt | P0 | PHÚC | FUNC-031 |
| PR-CAN-010 | Coverage dưới threshold PHẢI tạo warning và sensitivity run top 12/15 nếu được yêu cầu | P1 | PHÚC | FUNC-031 |
| PR-CAN-011 | Sensitivity run PHẢI có run/config ID riêng và không thay đổi QUBO 20-bit baseline âm thầm | P0 | PHÚC/TÂN | FUNC-032 |

## 10.3. Stress-to-cash policy

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-CAN-012 | Engine PHẢI ánh xạ `p_stress` thành target cash increment `B_t` theo approved policy | P0 | TÚ/PHÚC | FUNC-033 |
| PR-CAN-013 | Mapping PHẢI đơn điệu theo `p_stress` | P0 | TÚ/PHÚC | FUNC-034 |
| PR-CAN-014 | Threshold, target, hard cap và tolerance PHẢI nằm trong Config Registry | P0 | PHÚC/NGOC | FUNC-036, TBD-004 |
| PR-CAN-015 | Stress policy PHẢI được hiệu chỉnh trên validation 2023 và khóa trước test | P0 | TÚ/PHÚC | FUNC-035 |

---

# 11. OBJECTIVE SAMPLING VÀ QUBO REQUIREMENTS

## 11.1. Action encoding

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-QUB-001 | Mỗi candidate PHẢI có hai bits theo đúng candidate order | P0 | TÂN | FUNC-037 |
| PR-QUB-002 | Mapping bắt buộc là `00→0%`, `10→10%`, `01→20%`, `11→30%` vị thế hiện tại | P0 | TÂN/PHÚC | FUNC-038, BR-006 |
| PR-QUB-003 | Bitstring baseline PHẢI có đúng 20 ký tự thuộc `{0,1}` | P0 | TÂN | FUNC-039 |
| PR-QUB-004 | Encode và decode PHẢI là hàm nghịch đảo trên toàn bộ action grid | P0 | TÂN | NFR-001 |
| PR-QUB-005 | Dashboard sort order KHÔNG ĐƯỢC ảnh hưởng bit mapping | P0 | TÂN | FUNC-040 |

## 11.2. Objective sampling

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-QUB-006 | Objective Sampler PHẢI gọi canonical financial objective của Risk Engine | P0 | PHÚC/TÂN | FUNC-044 |
| PR-QUB-007 | Structured sample set PHẢI có intercept, 20 main effects và 190 pairwise effects, tổng tối thiểu 211 evaluations | P0 | TÂN/PHÚC | FUNC-044 |
| PR-QUB-008 | Validation/random samples PHẢI tách khỏi samples dùng fit surrogate | P0 | TÂN | FUNC-045 |
| PR-QUB-009 | Mỗi sample PHẢI lưu bitstring, decoded actions, objective components, scalar objective và violations | P0 | PHÚC/TÂN | OUT-TECH-008 |
| PR-QUB-010 | Sampling process PHẢI có seed và sampling policy version | P1 | TÂN | FUNC-045 |

## 11.3. Surrogate fitting và validation

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-QUB-011 | QUBO Builder PHẢI fit một quadratic surrogate từ approved objective samples | P0 | TÂN | FUNC-046 |
| PR-QUB-012 | QUBO package PHẢI lưu `Q`, linear terms, constant, scaling, penalties, candidate order và config hash | P0 | TÂN | OUT-TECH-009 |
| PR-QUB-013 | Validation PHẢI báo objective error, rank correlation, top-k recall, feasibility classification và stability | P0 | TÂN | FUNC-046 |
| PR-QUB-014 | Surrogate thresholds PHẢI được khóa trước test | P0 | TÂN/PHÚC | TBD-006 |
| PR-QUB-015 | Surrogate fail threshold PHẢI tạo `ERR_QUBO_SURROGATE_VALIDATION`; QAOA không được chạy như run hợp lệ | P0 | TÂN | FUNC-047 |
| PR-QUB-016 | Regularization và penalty coefficients PHẢI được version và không hard-code | P0 | TÂN | TBD-006 |
| PR-QUB-017 | QUBO package PHẢI có deterministic hash dùng để đối chiếu mọi solver | P0 | TÂN | FUNC-051 |

---

# 12. SOLVER VÀ QUANTUM REQUIREMENTS

## 12.1. Exact solver

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-SLV-001 | Exact solver PHẢI tìm global optimum của cùng QUBO 20-bit | P0 | TÂN | FUNC-048 |
| PR-SLV-002 | Brute-force implementation PHẢI đánh giá đủ `1.048.576` bitstrings hoặc chứng minh phương pháp exact tương đương | P0 | TÂN | FUNC-048 |
| PR-SLV-003 | Exact output PHẢI lưu best bitstring, energy, feasibility, runtime và QUBO hash | P0 | TÂN | FUNC-052 |
| PR-SLV-004 | Exact solver PHẢI là reference cho QUBO-level optimality, không được mô tả là bằng chứng financial global optimum | P0 | TÂN/NGOC | Section 11.4 PSS |

## 12.2. Warm-start QAOA

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-SLV-005 | Quantum solver chính PHẢI là Warm-start QAOA p=1 | P0 | TÂN | FUNC-049 |
| PR-SLV-006 | QAOA p=2 CÓ THỂ chạy như challenger và không chặn R1 | P2 | TÂN | FUNC-049 |
| PR-SLV-007 | Baseline candidate PHẢI dùng 1.024 shots và tối thiểu 10 pre-registered seeds | P1 | TÂN | FUNC-050 |
| PR-SLV-008 | Mỗi seed PHẢI lưu optimizer, initial point, circuit depth, shots, backend và package versions | P0 | TÂN | FUNC-052 |
| PR-SLV-009 | QAOA PHẢI dùng cùng QUBO hash với exact solver | P0 | TÂN | FUNC-051 |
| PR-SLV-010 | Hệ thống KHÔNG ĐƯỢC chỉ giữ seed tốt nhất; summary phải bao gồm toàn bộ seed | P0 | TÂN | FUNC-053 |
| PR-SLV-011 | Solver output PHẢI lưu sample distribution hoặc top measured bitstrings cùng counts/probabilities | P0 | TÂN | FUNC-052 |

## 12.3. Classical baseline và benchmark

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-SLV-012 | Benchmark PHẢI có ít nhất exact reference và một classical heuristic/baseline trên cùng QUBO | P0 | TÂN | FUNC-051–052 |
| PR-SLV-013 | Benchmark PHẢI báo best feasible energy, optimality gap, feasible rate, optimum sampling probability và runtime | P0 | TÂN | FUNC-052 |
| PR-SLV-014 | Runtime comparison PHẢI ghi hardware/backend và không được diễn giải sai giữa simulator và classical CPU | P0 | TÂN/NGOC | Section 11.5 PSS |
| PR-SLV-015 | QAOA failure/timeout PHẢI kích hoạt exact/classical fallback và actual solver phải hiển thị rõ | P0 | TÂN | FUNC-054 |

---

# 13. TRUE RE-RANKING, POLISHING VÀ PORTFOLIO ACCOUNTING

## 13.1. Candidate consolidation và true re-ranking

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-FIN-001 | Hệ thống PHẢI hợp nhất distinct feasible bitstrings từ QAOA, exact và classical results | P0 | TÂN | FUNC-055 |
| PR-FIN-002 | Candidate pool PHẢI giữ solver provenance và sampling probability | P1 | TÂN | FUNC-055 |
| PR-FIN-003 | Top 10–20 candidates PHẢI được Risk Engine tính lại bằng canonical financial objective | P0 | PHÚC | FUNC-056 |
| PR-FIN-004 | Mỗi candidate PHẢI có true CVaR, expected return, cost, turnover, liquidity penalty, cash deviation và violations | P0 | PHÚC | FUNC-056 |
| PR-FIN-005 | Final coarse candidate PHẢI được chọn bằng true financial objective, không chỉ bằng QUBO energy | P0 | PHÚC/NGOC | FUNC-057 |
| PR-FIN-006 | Hệ thống PHẢI báo surrogate rank, true rank và ranking disagreement | P1 | PHÚC/TÂN | FUNC-058 |

## 13.2. Local polishing

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-FIN-007 | Polishing PHẢI khóa active set: Quantum action 0% giữ nguyên 0% | P0 | PHÚC | FUNC-059–060 |
| PR-FIN-008 | Non-zero action chỉ được điều chỉnh tối đa ±5 điểm phần trăm | P0 | PHÚC | FUNC-061 |
| PR-FIN-009 | Final reduction PHẢI nằm trong `[0,30%]` và không vượt vị thế hiện tại | P0 | PHÚC | FUNC-061 |
| PR-FIN-010 | Polishing PHẢI dùng same true financial objective và constraints | P0 | PHÚC | FUNC-062 |
| PR-FIN-011 | Output PHẢI lưu quantum action, polished action, absolute change và objective improvement | P0 | PHÚC | FUNC-062 |
| PR-FIN-012 | Hệ thống PHẢI tính polishing dependency metric; dependency cao phải tạo warning | P1 | PHÚC/TÂN | FUNC-063 |

## 13.3. Portfolio accounting

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-FIN-013 | Mức giảm PHẢI áp dụng trên value của vị thế hiện tại, không áp dụng trực tiếp như điểm % NAV | P0 | PHÚC | FUNC-064, BR-006 |
| PR-FIN-014 | Gross proceeds PHẢI bằng tổng position value nhân final reduction | P0 | PHÚC | FUNC-064 |
| PR-FIN-015 | Transaction cost PHẢI được trừ khỏi proceeds/cash và NAV | P0 | PHÚC | FUNC-065–066 |
| PR-FIN-016 | Final stock weights + cash weight PHẢI bằng 1 trong `epsilon_w` | P0 | PHÚC/TÂN | FUNC-067 |
| PR-FIN-017 | Không final weight nào được âm; không action nào vượt 30% hoặc vượt available position | P0 | PHÚC | FUNC-068 |
| PR-FIN-018 | Accounting check fail PHẢI chặn dashboard recommendation và tạo `ERR_FIN_ACCOUNTING` | P0 | PHÚC/TÂN | BR-020 |

---

# 14. DASHBOARD VÀ REPORTING REQUIREMENTS

## 14.1. Information architecture

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-UI-001 | Dashboard PHẢI có khu vực Portfolio Input/Run Selection | P1 | TÂN | FUNC-069 |
| PR-UI-002 | Dashboard PHẢI có Market Regime panel với state probabilities và interpretation | P1 | TÂN/TÚ | FUNC-070 |
| PR-UI-003 | Dashboard PHẢI có Baseline Risk panel với CVaR/VaR/drawdown và confidence interval | P0 | TÂN/PHÚC | FUNC-071 |
| PR-UI-004 | Dashboard PHẢI có Candidate panel với top 10, score breakdown và coverage | P1 | TÂN/PHÚC | FUNC-072 |
| PR-UI-005 | Dashboard PHẢI có Quantum panel với bit mapping, raw actions, QAOA probabilities và benchmark | P0 | TÂN | FUNC-073, FUNC-075 |
| PR-UI-006 | Dashboard PHẢI có Final Recommendation panel phân biệt raw Quantum và polished actions | P0 | TÂN | FUNC-073–074 |
| PR-UI-007 | Dashboard PHẢI có Before–After panel gồm risk, return, turnover, cost, cash và weights | P0 | TÂN/PHÚC | FUNC-074 |
| PR-UI-008 | Dashboard PHẢI có Audit/Limitations panel với run ID, versions, solver, fallback và disclaimer | P0 | TÂN/NGOC | FUNC-077–078 |

## 14.2. Data integrity trên UI

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-UI-009 | Dashboard PHẢI đọc số liệu từ versioned artifacts của một run | P0 | TÂN | FUNC-076 |
| PR-UI-010 | Dashboard KHÔNG ĐƯỢC có implementation CVaR, cost hoặc accounting độc lập | P0 | TÂN | BR-018 |
| PR-UI-011 | Mỗi metric PHẢI có label, unit, confidence level và source run | P1 | TÂN | NFR-015 |
| PR-UI-012 | UI sort/filter KHÔNG ĐƯỢC thay đổi candidate order dùng decode | P0 | TÂN | PR-QUB-005 |
| PR-UI-013 | Cached/offline result PHẢI hiển thị data timestamp và không được mô tả là real-time | P0 | TÂN/NGOC | OOS-003 |

## 14.3. Nội dung và xuất báo cáo

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-UI-014 | Export PHẢI gồm portfolio input, evaluation date, config version, methodology, results, assumptions và limitations | P1 | NGOC/TÂN | FUNC-077 |
| PR-UI-015 | Final action table PHẢI gồm ticker, old weight, bits, Quantum reduction, polished reduction, sell value và new weight | P0 | TÂN/PHÚC | OUT-006 |
| PR-UI-016 | Kết quả fallback PHẢI ghi requested solver, actual solver và reason | P0 | TÂN | PR-SLV-015 |
| PR-UI-017 | Nếu CVaR không cải thiện, UI PHẢI hiển thị trạng thái không cải thiện và không dùng màu/ngôn ngữ gây hiểu nhầm | P0 | NGOC/TÂN | KPI-014 |
| PR-UI-018 | Disclaimer PHẢI nêu đây là decision-support, không tự đặt lệnh, không bảo đảm lợi nhuận | P0 | NGOC | OOS-001, OOS-014 |

---

# 15. CONFIGURATION, REGISTRY VÀ CHANGE CONTROL REQUIREMENTS

## 15.1. Config Registry

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-CFG-001 | Mọi tham số có thể thay đổi PHẢI nằm trong versioned Config Registry hoặc module config được registry tham chiếu | P0 | NGOC/TÂN | DEP-003 |
| PR-CFG-002 | Config PHẢI có version, status, approver, effective date, change reason và hash | P0 | NGOC/TÂN | Section 23 PSS |
| PR-CFG-003 | Code KHÔNG ĐƯỢC chứa một giá trị khác với approved config mà không có explicit override record | P0 | TÂN | NFR-022 |
| PR-CFG-004 | Run manifest PHẢI lưu exact config version/hash | P0 | TÂN | FUNC-078 |
| PR-CFG-005 | Approved config KHÔNG ĐƯỢC sửa tại chỗ; thay đổi phải tạo version mới | P0 | NGOC/TÂN | NFR-008 |
| PR-CFG-006 | Override trong development PHẢI được gắn `NON_BASELINE_RUN` | P1 | TÂN | Section 22 PSS |

## 15.2. Registries

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-CFG-007 | Data Registry PHẢI quản lý data version, source, date range và checksum | P0 | MINHANH | DEP-001–002 |
| PR-CFG-008 | Model Registry PHẢI quản lý HMM/scenario version, feature version, train window và validation status | P0 | TÚ | FUNC-013, FUNC-021 |
| PR-CFG-009 | Financial Policy Registry PHẢI quản lý cost, liquidity, objective weights và stress policy | P0 | PHÚC/NGOC | TBD-002–005 |
| PR-CFG-010 | Quantum Registry PHẢI quản lý QUBO version/hash, solver config, backend và package versions | P0 | TÂN | TBD-006–007 |

## 15.3. Change control

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-CFG-011 | Thay universe logic, primary metric, action grid, Quantum dimension hoặc instrument PHẢI có Change Request | P0 | NGOC | Section 22 PSS |
| PR-CFG-012 | Change Request PHẢI nêu requirements, schemas, tests, artifacts và migration bị ảnh hưởng | P1 | NGOC/TÂN | Section 22.2 PSS |
| PR-CFG-013 | Requirement bị deprecated PHẢI có replacement ID hoặc lý do loại bỏ | P1 | NGOC | Section 2.3 PRS |

---

# 16. AUDIT, EVIDENCE VÀ REPRODUCIBILITY REQUIREMENTS

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-AUD-001 | Mỗi run PHẢI có `run_manifest.json` | P0 | TÂN | OUT-TECH-001 |
| PR-AUD-002 | Manifest PHẢI chứa data, model, config, QUBO, dashboard và code versions | P0 | TÂN | FUNC-078 |
| PR-AUD-003 | Mỗi random module PHẢI lưu seed hoặc seed list | P0 | TÚ/TÂN | FUNC-080 |
| PR-AUD-004 | Mỗi artifact PHẢI có producer, timestamp, schema version và run ID | P0 | TÂN | NFR-007 |
| PR-AUD-005 | Mỗi metric trong report/dashboard PHẢI truy xuất được về artifact và script | P0 | TÂN/NGOC | FUNC-079 |
| PR-AUD-006 | Logs PHẢI ghi module start/end, status, warnings, error code và fallback | P1 | TÂN | NFR-006 |
| PR-AUD-007 | Release PHẢI có package/environment lockfile hoặc environment manifest | P0 | TÂN | NFR-005 |
| PR-AUD-008 | Exact run với cùng input/config/version PHẢI tái lập bitstring và energy | P0 | TÂN | NFR-003 |
| PR-AUD-009 | QAOA run PHẢI tái lập theo registered seed list và backend versions trong tolerance | P1 | TÂN | NFR-004 |
| PR-AUD-010 | Một thành viên ngoài module owner PHẢI chạy lại release candidate theo runbook trước UAT sign-off | P1 | TOÀN ĐỘI | FUNC-081 |
| PR-AUD-011 | Báo cáo KHÔNG ĐƯỢC chứa số liệu nhập tay không có artifact | P0 | NGOC | BR-018–019 |
| PR-AUD-012 | Test evidence PHẢI liên kết requirement ID, AC ID, test ID và artifact path | P0 | NGOC/PHÚC | DEP-008 |

---

# 17. OPERATIONS, FALLBACK VÀ DEPLOYMENT REQUIREMENTS

| ID | Yêu cầu bắt buộc | Priority | Owner | Scope trace |
|---|---|---:|---|---|
| PR-OPS-001 | R1 PHẢI chạy được local/offline bằng documented command | P0 | TÂN | NFR-011 |
| PR-OPS-002 | Dashboard PHẢI hỗ trợ xem validated cached run khi solver không thể chạy trong demo | P1 | TÂN | NFR-012 |
| PR-OPS-003 | Cached run PHẢI giữ nguyên run ID, data/config/model versions và timestamp | P0 | TÂN | PR-UI-013 |
| PR-OPS-004 | Module failure PHẢI tạo structured error, không chỉ stack trace | P0 | TÂN | NFR-009, NFR-016 |
| PR-OPS-005 | Critical failure PHẢI chặn final recommendation | P0 | TÂN | BR-020 |
| PR-OPS-006 | QAOA timeout PHẢI fallback theo config và đổi run status thành `COMPLETED_WITH_FALLBACK` nếu các gate khác pass | P0 | TÂN | PR-SLV-015 |
| PR-OPS-007 | HMM/scenario fallback chỉ được dùng nếu model đã approved; không tự chọn model chưa validation | P0 | TÚ/TÂN | PR-REG-014, PR-SCN-013 |
| PR-OPS-008 | Deployment guide PHẢI ghi dependencies, environment setup, run command, cache path và recovery steps | P1 | TÂN | DEL-015 |
| PR-OPS-009 | Hệ thống KHÔNG ĐƯỢC kết nối broker hoặc gửi order | P0 | TÂN | OOS-001 |
| PR-OPS-010 | Runtime, memory và reference hardware PHẢI được ghi trong final benchmark | P1 | TÂN | NFR-013 |

---

# 18. NON-FUNCTIONAL REQUIREMENTS

## 18.1. Correctness và numerical integrity

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-COR-001 | Các hàm CVaR, cost, turnover, encode/decode và accounting PHẢI có unit tests | P0 | PHÚC/TÂN |
| PR-NFR-COR-002 | Float comparison PHẢI dùng tolerance từ Config Registry, không so sánh equality tùy tiện | P0 | TÂN |
| PR-NFR-COR-003 | Ticker order và unit conversion PHẢI được kiểm tra tại mọi interface boundary | P0 | TOÀN ĐỘI |
| PR-NFR-COR-004 | Hệ thống PHẢI từ chối `NaN`, `Inf` và values ngoài domain trước module tiếp theo | P0 | TOÀN ĐỘI |
| PR-NFR-COR-005 | Financial sign convention PHẢI được mô tả và test xuyên suốt | P0 | PHÚC |

## 18.2. Reliability và recoverability

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-REL-001 | Module PHẢI fail explicitly và không phát hành partial result như completed result | P0 | TÂN |
| PR-NFR-REL-002 | Approved fallback PHẢI có regression tests | P1 | TÚ/TÂN |
| PR-NFR-REL-003 | Artifacts đã hoàn tất PHẢI được ghi atomically hoặc có completion marker | P1 | TÂN |
| PR-NFR-REL-004 | Run lại sau lỗi PHẢI tạo run mới hoặc resume theo documented rule; không ghi đè im lặng | P0 | TÂN |

## 18.3. Reproducibility

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-REP-001 | Same exact input/config/version PHẢI tạo same deterministic outputs | P0 | TOÀN ĐỘI |
| PR-NFR-REP-002 | Stochastic outputs PHẢI tái lập theo seed/backend/version hoặc báo tolerance | P1 | TÚ/TÂN |
| PR-NFR-REP-003 | Release PHẢI có immutable manifest và checksums cho critical artifacts | P1 | TÂN |

## 18.4. Performance

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-PERF-001 | UI dùng cached artifacts PHẢI phản hồi thao tác phổ biến trong SLA được khóa sau benchmark | P1 | TÂN |
| PR-NFR-PERF-002 | QAOA KHÔNG ĐƯỢC chạy lại khi người dùng chỉ thay filter/sort hiển thị | P0 | TÂN |
| PR-NFR-PERF-003 | Exact enumeration PHẢI được vectorize/batched đủ để chạy trên reference hardware đã công bố | P1 | TÂN |
| PR-NFR-PERF-004 | 2.000/5.000 scenarios PHẢI được xử lý mà không vượt memory budget đã benchmark | P1 | TÚ/PHÚC |
| PR-NFR-PERF-005 | Development mode CÓ THỂ giảm shots/seeds nhưng phải gắn `NON_FINAL_CONFIG` | P1 | TÂN |

## 18.5. Security và privacy

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-SEC-001 | Không yêu cầu hoặc lưu PII cho core analysis | P0 | NGOC/TÂN |
| PR-NFR-SEC-002 | Uploaded file PHẢI được kiểm tra extension, schema và size | P1 | TÂN |
| PR-NFR-SEC-003 | Secrets PHẢI được nạp từ environment/secret store, không từ repository | P0 | MINHANH/TÂN |
| PR-NFR-SEC-004 | Log KHÔNG ĐƯỢC chứa credential hoặc token | P0 | TÂN |
| PR-NFR-SEC-005 | Không có broker credential hoặc order execution endpoint trong R1 | P0 | TÂN |

## 18.6. Usability và accessibility

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-UX-001 | Metric PHẢI có tên, unit và diễn giải ngắn bằng ngôn ngữ tài chính nhất quán | P1 | NGOC |
| PR-NFR-UX-002 | Màu sắc không được là tín hiệu duy nhất cho trạng thái pass/fail/risk | P2 | TÂN |
| PR-NFR-UX-003 | Warning/failure PHẢI có text rõ ràng và hướng xử lý | P1 | NGOC/TÂN |
| PR-NFR-UX-004 | Quantum raw result và polished final result PHẢI tách biệt trực quan | P0 | TÂN |
| PR-NFR-UX-005 | Dashboard PHẢI hiển thị disclaimer tại khu vực kết quả cuối | P0 | NGOC/TÂN |

## 18.7. Explainability và model governance

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-EXP-001 | HMM state PHẢI có profile và narrative dựa trên metrics | P1 | TÚ/PHÚC |
| PR-NFR-EXP-002 | Candidate selection PHẢI giải thích score components | P1 | PHÚC |
| PR-NFR-EXP-003 | Final action PHẢI truy xuất về bits, Quantum action và polishing delta | P0 | TÂN/PHÚC |
| PR-NFR-EXP-004 | Báo cáo PHẢI nêu model risk, scenario risk, survivorship bias và QUBO approximation | P0 | NGOC |
| PR-NFR-EXP-005 | Không được mô tả correlation hoặc model output như quan hệ nhân quả | P0 | NGOC/TÚ |

## 18.8. Maintainability và interoperability

| ID | Yêu cầu | Priority | Owner |
|---|---|---:|---|
| PR-NFR-MNT-001 | Data, AI, Risk, Quantum và UI PHẢI tách module với interface rõ | P0 | TÂN |
| PR-NFR-MNT-002 | Shared schemas PHẢI có version và validation code | P0 | MINHANH/TÂN |
| PR-NFR-MNT-003 | Thay schema PHẢI có migration note và regression tests | P1 | TÂN |
| PR-NFR-MNT-004 | Core logic KHÔNG ĐƯỢC chỉ tồn tại trong notebook | P0 | TOÀN ĐỘI |
| PR-NFR-MNT-005 | Notebook dùng phân tích PHẢI gọi shared modules cho metric chính | P1 | TOÀN ĐỘI |

---

# 19. CANONICAL INTERFACE CONTRACTS Ở CẤP PRODUCT

Phần này khóa trường tối thiểu. Type chi tiết và nullable rules nằm trong Data Contract.

## 19.1. Portfolio request

```yaml
portfolio_request:
  evaluation_date: date
  positions:
    - ticker: string
      value_or_weight: number
  cash_value_or_weight: number
  input_unit: value|weight
  run_mode: development|final
  requested_solver: qaoa|exact|classical
```

## 19.2. Regime output

```yaml
regime_output:
  run_id: string
  evaluation_date: date
  model_version: string
  selected_state: integer
  selected_label: normal|volatile|stress
  state_probabilities: map
  p_stress: number
  quality_gate: pass|fail
```

## 19.3. Candidate order

```yaml
candidate_order:
  run_id: string
  config_version: string
  candidates:
    - rank: integer
      ticker: string
      current_weight: number
      marginal_cvar_reduction: number
      transaction_cost_proxy: number
      liquidity_penalty: number
      candidate_score: number
  risk_coverage: number
```

## 19.4. Solver result

```yaml
solver_result:
  run_id: string
  qubo_hash: string
  solver: exact|qaoa|classical
  solver_config: map
  candidates:
    - bitstring: string
      qubo_energy: number
      feasible: boolean
      probability_or_count: number|null
  runtime_seconds: number
  status: completed|failed|timeout
```

## 19.5. Final recommendation

```yaml
final_recommendation:
  run_id: string
  requested_solver: string
  actual_solver: string
  evaluation_date: date
  actions:
    - ticker: string
      bits: string
      quantum_reduction: number
      polished_reduction: number
      current_weight: number
      sell_value: number
      final_weight: number
  cash_before: number
  cash_after: number
  cvar_before: map
  cvar_after: map
  expected_return_before: number
  expected_return_after: number
  transaction_cost: number
  turnover: number
  constraints_passed: boolean
  warnings: list
```

---

# 20. ERROR TAXONOMY

| Prefix | Module | Ví dụ |
|---|---|---|
| `ERR_RUN_*` | Intake/lifecycle | Invalid state transition |
| `ERR_DATA_*` | Data/eligibility | Schema, leakage, coverage |
| `ERR_REGIME_*` | HMM | Non-convergence, invalid probabilities |
| `ERR_SCENARIO_*` | Scenario | Invalid shape, failed validation |
| `ERR_RISK_*` | Risk | CVaR, cost hoặc objective error |
| `ERR_CANDIDATE_*` | Candidate | Insufficient candidates, low coverage |
| `ERR_QUBO_*` | QUBO | Invalid mapping, surrogate fail |
| `ERR_SOLVER_*` | Solver | Timeout, backend failure, no feasible sample |
| `ERR_FIN_*` | Re-ranking/accounting | Invalid weights, cost reconciliation |
| `ERR_UI_*` | Presentation | Missing artifact, version mismatch |

Mỗi lỗi phải có:

- `error_code` ổn định.
- Human-readable message.
- Module và timestamp.
- Run ID nếu đã tồn tại.
- Có thể retry hay không.
- Recommended action.
- Root exception chỉ lưu trong technical log.

---

# 21. QUALITY GATES

| Gate ID | Gate | Điều kiện tối thiểu | Owner | Chặn release |
|---|---|---|---|---:|
| GATE-01 | Scope/Config Gate | Scope, Decision Log và Config Registry nhất quán | NGOC | Có |
| GATE-02 | Data Gate | Schema, temporal integrity, eligibility và DQ pass | MINHANH | Có |
| GATE-03 | Regime Gate | HMM converged, stable và interpretable | TÚ | Có |
| GATE-04 | Scenario Gate | Scenario validation pass | TÚ/PHÚC | Có |
| GATE-05 | Risk Gate | CVaR/cost/accounting unit tests pass | PHÚC | Có |
| GATE-06 | Candidate Gate | Top 10 deterministic và coverage reported | PHÚC | Có |
| GATE-07 | QUBO Gate | Surrogate validation pass và hash được khóa | TÂN/PHÚC | Có |
| GATE-08 | Solver Gate | Exact reference và QAOA/classical benchmark hợp lệ | TÂN | Có |
| GATE-09 | Finance Gate | True re-ranking, zero-lock, bounds và accounting pass | PHÚC | Có |
| GATE-10 | Product Gate | Dashboard reconciliation, UAT và disclaimer pass | NGOC | Có |

---

# 22. TRACEABILITY MATRIX CẤP MODULE

| Scope range | Product requirement range | Module owner | Consumer | Evidence chính |
|---|---|---|---|---|
| FUNC-001–005 | PR-RUN-001–012 | NGOC/TÂN | Toàn pipeline | Portfolio input, validation log |
| FUNC-006–010, DATA-001–015 | PR-DAT-001–020 | MINHANH | TÚ/PHÚC | Universe, DQ, eligibility |
| FUNC-011–015 | PR-REG-001–015 | TÚ | Scenario Engine | Model-selection report, regime output |
| FUNC-016–021 | PR-SCN-001–015 | TÚ | PHÚC | Scenario cube, validation report |
| FUNC-022–027 | PR-RSK-001–020 | PHÚC | CAN/QUB/UI | Risk result, objective tests |
| FUNC-028–036 | PR-CAN-001–015 | PHÚC/TÚ | QUBO Builder | Candidate order, coverage, cash policy |
| FUNC-037–047 | PR-QUB-001–017 | TÂN/PHÚC | Solver Layer | Samples, QUBO, validation |
| FUNC-048–054 | PR-SLV-001–015 | TÂN | Re-ranking | Exact/QAOA/classical result |
| FUNC-055–068 | PR-FIN-001–018 | PHÚC/TÂN | Dashboard | Re-ranking, polishing, final portfolio |
| FUNC-069–077 | PR-UI-001–018 | TÂN/NGOC | User/Judge | Dashboard, export report |
| FUNC-078–081 | PR-CFG/PR-AUD/PR-OPS | TÂN/NGOC | QA/UAT | Manifests, logs, runbook |
| NFR-001–023 | PR-NFR-* | Toàn đội | Product Gate | Test evidence, benchmark |

---

# 23. OPEN REQUIREMENT DEPENDENCIES

Các requirement sau chỉ chuyển sang `Approved` sau khi Config Registry khóa giá trị:

| Open ID | Requirement bị ảnh hưởng | Quyết định cần khóa |
|---|---|---|
| OPEN-001 | PR-DAT-001–004 | Universe list, snapshot date và source |
| OPEN-002 | PR-DAT-016 | Minimum history, coverage và liquidity threshold |
| OPEN-003 | PR-RSK-009–013 | Fee, tax, slippage và liquidity model |
| OPEN-004 | PR-RSK-015–018 | Objective weights và scaling |
| OPEN-005 | PR-CAN-004, PR-CAN-009–010 | Candidate weights và coverage threshold |
| OPEN-006 | PR-CAN-012–015 | Stress thresholds, `B_t`, hard cap và tolerance |
| OPEN-007 | PR-QUB-013–016 | Surrogate metrics, thresholds, penalty và regularization |
| OPEN-008 | PR-SLV-007–015 | Seed list, optimizer, timeout và fallback threshold |
| OPEN-009 | PR-NFR-PERF-* | Performance SLA và reference hardware |

Việc còn `OPEN` không cho phép từng module tự chọn giá trị riêng. Development có thể dùng config ở trạng thái `DRAFT`, nhưng mọi run phải gắn `NON_BASELINE_RUN` cho đến khi được phê duyệt.

---

# 24. REQUIREMENT ACCEPTANCE VÀ DEFINITION OF READY/DONE

## 24.1. Definition of Ready cho implementation

Một requirement chỉ được đưa vào development khi:

1. Có ID duy nhất và statement kiểm thử được.
2. Có scope trace, owner, priority và reviewer.
3. Input/output contract đã có hoặc có mock schema.
4. Các config cần thiết đã approved hoặc được gắn draft rõ ràng.
5. Acceptance Criteria và Test Case ID đã được tạo.
6. Dependency và error behavior được xác định.
7. Không mâu thuẫn với Product Scope và business invariants.

## 24.2. Definition of Done cho requirement

Requirement được xem là Done khi:

1. Implementation đã merge vào release branch.
2. Unit tests và integration tests pass.
3. Acceptance Criteria có evidence.
4. Artifact có version và run ID.
5. Reviewer ngoài module owner xác nhận.
6. RTM cập nhật trạng thái `Verified`.
7. Dashboard/report nếu liên quan khớp artifact.
8. Limitations và fallback được cập nhật.
9. Không có unresolved P0 defect.

---

# 25. PRODUCT REQUIREMENT APPROVAL

Product Requirements v1.0 được chuyển từ `Baseline Candidate` sang `Approved` khi:

- Product Scope `QSHIELD-PSS-001 v1.0` được phê duyệt.
- Config Registry khóa toàn bộ critical `OPEN` items.
- Năm module owner xác nhận requirements thuộc phạm vi mình.
- Requirement IDs được đưa vào RTM.
- Acceptance Criteria và Test Plan có coverage cho toàn bộ P0/P1 requirements.
- Không tồn tại mâu thuẫn giữa action semantics, candidate order, financial objective, QUBO và dashboard.

| Vai trò | Họ tên | Trạng thái | Ngày |
|---|---|---|---|
| Product Owner | Nguyễn Thị Ánh Ngọc | Chờ phê duyệt | TBD |
| Data Owner | Nguyễn Đỗ Minh Anh | Chờ xác nhận | TBD |
| AI/ML Owner | Nguyễn Anh Tú | Chờ xác nhận | TBD |
| Quant Risk Owner | Liêu Hoài Phúc | Chờ xác nhận | TBD |
| Technical/Quantum Owner | Đỗ Ngọc Tân | Chờ xác nhận | TBD |

---

# PHỤ LỤC A — MACHINE-READABLE REQUIREMENT SUMMARY

```yaml
product: Q-SHIELD
document: QSHIELD-PRS-001
version: 1.0
status: baseline_candidate
parent_scope: QSHIELD-PSS-001-v1.0

baseline:
  product_type: decision_support
  trading_execution: false
  universe_size: 30
  candidate_count: 10
  data_frequency: daily
  primary_risk_metric: CVaR_95
  action_levels: [0.00, 0.10, 0.20, 0.30]
  action_semantics: percentage_of_current_position
  bits_per_asset: 2
  total_bits: 20
  quantum_role: [active_set_selection, coarse_position_sizing]
  final_selection: true_financial_objective
  polishing_zero_lock: true
  polishing_maximum_adjustment_percentage_points: 5

requirement_domains:
  RUN: run_lifecycle_and_portfolio_intake
  DAT: data_universe_and_eligibility
  REG: market_regime_hmm
  SCN: scenario_generation
  RSK: risk_engine_and_financial_objective
  CAN: candidate_selection_and_stress_policy
  QUB: objective_sampling_and_qubo
  SLV: exact_classical_and_qaoa_solvers
  FIN: true_reranking_polishing_and_accounting
  UI: dashboard_and_reporting
  CFG: configuration_and_registries
  AUD: audit_and_reproducibility
  OPS: operations_and_fallback
  NFR: non_functional_requirements

release_blocking_gates:
  - scope_config
  - data
  - regime
  - scenario
  - risk
  - candidate
  - qubo
  - solver
  - finance
  - product_uat

prohibited_behaviors:
  - future_data_leakage
  - short_selling
  - leverage
  - derivative_hedging
  - buy_increase
  - automatic_order_execution
  - dashboard_side_financial_logic
  - seed_cherry_picking
  - final_selection_by_qubo_energy_only
  - polishing_activation_of_zero_quantum_action
  - quantum_advantage_claim_without_evidence
```

# PHỤ LỤC B — DISCLAIMER BẮT BUỘC

> Q-SHIELD là hệ thống hỗ trợ phân tích và ra quyết định quản trị rủi ro dựa trên dữ liệu lịch sử, mô hình thống kê, mô phỏng và tối ưu. Hệ thống không tự động đặt lệnh, không thay thế tư vấn đầu tư được cấp phép, không bảo đảm lợi nhuận và không bảo đảm ngăn ngừa tổn thất trong mọi điều kiện thị trường. Kết quả phụ thuộc vào dữ liệu, giả định chi phí, mô hình sinh kịch bản, QUBO surrogate và cấu hình solver.

---

**Kết thúc tài liệu — QSHIELD-PRS-001 v1.0 Baseline Candidate**
