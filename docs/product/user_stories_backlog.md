---
document_id: QSHIELD-US-001
document_title: Q-SHIELD User Stories and Product Backlog
document_version: 1.0
document_status: Baseline Candidate
product_name: Q-SHIELD
team_name: NOVARIS
parent_scope_document: QSHIELD-PSS-001-v1.0
parent_requirements_document: QSHIELD-PRS-001-v1.0
product_owner: Nguyễn Thị Ánh Ngọc
technical_owner: Đỗ Ngọc Tân
language: vi-VN
last_updated: 2026-08-02
---

# Q-SHIELD — USER STORIES VÀ PRODUCT BACKLOG

## Backlog nghiệp vụ cho hệ thống Quantum–AI hỗ trợ quản trị tail risk danh mục cổ phiếu

**Đội dự án:** NOVARIS  
**Product Owner:** Nguyễn Thị Ánh Ngọc  
**Tài liệu nguồn:** `QSHIELD-PSS-001 v1.0`, `QSHIELD-PRS-001 v1.0`  
**Trạng thái:** Baseline Candidate  
**Mục đích:** Chuyển Product Scope và Product Requirements thành các lát cắt giá trị có thể ưu tiên, phát triển, kiểm thử và demo.

---

# 1. MỤC ĐÍCH VÀ NGUYÊN TẮC

## 1.1. User Story là gì?

User Story mô tả một nhu cầu có giá trị dưới góc nhìn của người sử dụng hoặc bên liên quan:

> **Với tư cách là** `[actor]`, **tôi muốn** `[capability]`, **để** `[business value]`.

User Story không phải một task kỹ thuật đơn lẻ. Ví dụ, “viết hàm CVaR” là task; “xem tail risk của danh mục để đánh giá mức tổn thất trong kịch bản xấu” mới là User Story. Một story có thể cần nhiều task dữ liệu, mô hình, backend, UI và test để hoàn thành.

## 1.2. Nguyên tắc INVEST

Mỗi story nên đáp ứng:

- **Independent:** độc lập tương đối, không phụ thuộc không cần thiết.
- **Negotiable:** chi tiết implementation có thể thảo luận nhưng không phá business rule.
- **Valuable:** tạo giá trị cho actor hoặc giảm rủi ro sản phẩm.
- **Estimable:** đủ rõ để ước lượng.
- **Small:** có thể hoàn thành trong một sprint hoặc tách được.
- **Testable:** có outcome kiểm chứng được.

## 1.3. Quy ước ưu tiên

| Priority | Ý nghĩa |
|---|---|
| P0 | Chặn release nếu thiếu hoặc sai |
| P1 | Bắt buộc cho core product/UAT |
| P2 | Nên có; có thể defer có phê duyệt |
| P3 | Enhancement/Future backlog |

## 1.4. Quy ước trạng thái

`DRAFT → READY → IN_PROGRESS → IN_REVIEW → VERIFIED → ACCEPTED`

Story chỉ chuyển sang `ACCEPTED` khi Acceptance Criteria pass, evidence đầy đủ và Product Owner chấp thuận nếu story có tác động đến người dùng.

---

# 2. ACTORS VÀ PERSONAS

## ACT-001 — Portfolio User

Nhà đầu tư hoặc người quản lý danh mục đang nắm giữ cổ phiếu thuộc universe VN30 cố định của Q-SHIELD, không sử dụng phái sinh và muốn giảm tail risk bằng cách bán giảm vị thế rồi chuyển sang tiền mặt.

**Nhu cầu:** kết quả dễ hiểu, có giải thích, trước–sau rõ ràng, không tự đặt lệnh.

## ACT-002 — Product Owner

Người chịu trách nhiệm bảo đảm hệ thống giải đúng bài toán, requirement thống nhất, claim có evidence và UAT đạt.

**Đại diện:** Nguyễn Thị Ánh Ngọc.

## ACT-003 — Data Owner

Người quản lý universe, nguồn dữ liệu, schema, eligibility, temporal integrity và data quality.

**Đại diện:** Nguyễn Đỗ Minh Anh.

## ACT-004 — AI/ML Owner

Người quản lý HMM, model selection, state interpretation, scenario generation và model validation.

**Đại diện:** Nguyễn Anh Tú.

## ACT-005 — Quant Risk Analyst

Người quản lý CVaR, cost, turnover, liquidity, candidate scoring, financial objective, true re-ranking và polishing.

**Đại diện:** Liêu Hoài Phúc.

## ACT-006 — Technical/Quantum Owner

Người quản lý QUBO, exact/QAOA/classical solvers, integration, artifacts, dashboard và deployment.

**Đại diện:** Đỗ Ngọc Tân.

## ACT-007 — Model Validator/Judge

Người cần xem bằng chứng rằng dữ liệu, mô hình, Quantum benchmark và kết quả cuối đúng, minh bạch, tái lập được.

---

# 3. PRODUCT JOURNEY VÀ EPIC MAP

```text
EPIC-01 Portfolio & Run
   ↓
EPIC-02 Data, Universe & Eligibility
   ↓
EPIC-03 Regime Detection
   ↓
EPIC-04 Scenario Generation
   ↓
EPIC-05 Risk & Candidate Selection
   ↓
EPIC-06 Quantum Optimization
   ↓
EPIC-07 True Re-ranking, Polishing & Accounting
   ↓
EPIC-08 Dashboard & Reporting
   ↓
EPIC-09 Governance, Audit & Operations
```

| Epic | Giá trị chính | Owner chính |
|---|---|---|
| EPIC-01 | Nhập danh mục và quản lý lần chạy | NGOC/TÂN |
| EPIC-02 | Bảo đảm dữ liệu đúng và point-in-time | MINHANH |
| EPIC-03 | Hiểu trạng thái và xác suất stress | TÚ |
| EPIC-04 | Mô phỏng các đường đi thị trường bất lợi | TÚ |
| EPIC-05 | Đo tail risk và chọn top 10 | PHÚC |
| EPIC-06 | Quantum chọn active set và coarse sizing | TÂN |
| EPIC-07 | Kiểm định, tinh chỉnh và tạo danh mục cuối | PHÚC/TÂN |
| EPIC-08 | Trình bày, giải thích và export | NGOC/TÂN |
| EPIC-09 | Kiểm soát config, evidence và vận hành | TOÀN ĐỘI |

---

# 4. EPIC-01 — PORTFOLIO VÀ RUN MANAGEMENT

## US-RUN-001 — Nhập danh mục cần phân tích

**User Story**  
Với tư cách là Portfolio User, tôi muốn nhập ticker, giá trị hoặc tỷ trọng từng vị thế, tiền mặt và ngày đánh giá, để Q-SHIELD phân tích đúng danh mục của tôi.

**Giá trị:** Tạo đầu vào chuẩn cho toàn bộ pipeline.  
**Priority:** P0  
**Owner:** NGOC/TÂN  
**Requirement trace:** PR-RUN-001–004, PR-UI-001.

**Điều kiện trước:** Universe Registry và schema portfolio input tồn tại.

**Main flow:**

1. Người dùng chọn nhập theo giá trị hoặc tỷ trọng.
2. Người dùng nhập các ticker và vị thế tương ứng.
3. Người dùng nhập tiền mặt và evaluation date.
4. Hệ thống chuẩn hóa về internal weight unit.
5. Hệ thống hiển thị bản xem trước trước khi chạy.

**Output:** `portfolio_request`, tổng NAV/weight, evaluation date và input preview.

**Ngoại lệ:** Ticker trùng, vị thế âm, thiếu cash hoặc sai ngày chuyển sang US-RUN-002.

## US-RUN-002 — Nhận phản hồi đầu vào không hợp lệ

**User Story**  
Với tư cách là Portfolio User, tôi muốn biết chính xác trường nào sai và cách sửa, để không chạy mô hình trên một danh mục không hợp lệ.

**Giá trị:** Ngăn lỗi lan truyền sang tài chính và Quantum.  
**Priority:** P0  
**Owner:** TÂN/MINHANH  
**Requirement trace:** PR-RUN-005–006, PR-OPS-004.

**Main flow:**

1. Hệ thống kiểm tra schema, ticker, values, cash và tổng weight.
2. Mỗi lỗi được trả bằng error code và human-readable message.
3. Input lỗi không tạo recommendation run.
4. Người dùng sửa và gửi lại.

**Output:** validation report, danh sách lỗi và recommended action.

**Quy tắc:** Hệ thống không được âm thầm xóa ticker hoặc normalize weight mà người dùng không biết.

## US-RUN-003 — Chọn chế độ development hoặc final

**User Story**  
Với tư cách là Portfolio User hoặc Model Validator, tôi muốn chọn chế độ development hoặc final, để cân bằng thời gian chạy và độ ổn định của kết quả.

**Priority:** P1  
**Owner:** TÂN/TÚ  
**Requirement trace:** PR-RUN-007, PR-SCN-002, PR-NFR-PERF-005.

**Main flow:**

- Development: 2.000 scenarios và cấu hình solver development đã đăng ký.
- Final: 5.000 scenarios và cấu hình benchmark chính thức.
- UI phải gắn nhãn rõ mode; development result không được dùng như final evidence.

**Output:** `run_mode`, requested/actual scenario count và config version.

## US-RUN-004 — Theo dõi trạng thái pipeline

**User Story**  
Với tư cách là Portfolio User, tôi muốn biết hệ thống đang ở bước nào, để phân biệt đang xử lý, hoàn tất, fallback hay thất bại.

**Priority:** P1  
**Owner:** TÂN  
**Requirement trace:** PR-RUN-008, PR-RUN-012, PR-OPS-004–006.

**Main flow:** UI hiển thị state hiện tại theo run state machine, module đang chạy, elapsed time và warning nếu có.

**Output:** live/cached run status, timestamp và module status.

**Ngoại lệ:** Khi một module fail, status không được hiển thị `COMPLETED`.

## US-RUN-005 — Chạy lại một phân tích what-if

**User Story**  
Với tư cách là Portfolio User, tôi muốn thay đổi danh mục hoặc cấu hình được phép rồi tạo một run mới, để so sánh các tình huống mà không làm mất kết quả cũ.

**Priority:** P1  
**Owner:** TÂN/NGOC  
**Requirement trace:** PR-RUN-009, PR-NFR-REL-004.

**Main flow:**

1. Người dùng chọn một run cũ làm template.
2. Hệ thống copy input/config reference, không copy final output.
3. Người dùng thay đổi field được phép.
4. Hệ thống tạo run ID mới.

**Quy tắc:** Run đã hoàn tất là bất biến.

## US-RUN-006 — Xử lý khi không đủ 10 ứng viên

**User Story**  
Với tư cách là Portfolio User, tôi muốn vẫn nhận được risk analysis khi danh mục có ít hơn 10 vị thế hợp lệ, đồng thời được thông báo rằng Quantum 20-bit không thể chạy, để tránh kết quả bị padding hoặc diễn giải sai.

**Priority:** P0  
**Owner:** NGOC/TÂN  
**Requirement trace:** PR-RUN-010, PR-DAT-019.

**Output:** baseline risk report và trạng thái `INSUFFICIENT_QUANTUM_CANDIDATES`; không có final Quantum recommendation.

---

# 5. EPIC-02 — DATA, UNIVERSE VÀ ELIGIBILITY

## US-DAT-001 — Sử dụng universe đã được phê duyệt

**User Story**  
Với tư cách là Data Owner, tôi muốn quản lý danh sách 30 mã VN30 bằng Universe Registry có version và snapshot date, để mọi module dùng cùng một universe.

**Priority:** P0  
**Owner:** MINHANH  
**Requirement trace:** PR-DAT-001–004, PR-CFG-007.

**Output:** approved Universe Registry, universe version và checksum.

**Quy tắc:** Thay một ticker phải tạo version mới; không sửa universe của run cũ.

## US-DAT-002 — Kiểm tra chất lượng dữ liệu

**User Story**  
Với tư cách là Data Owner, tôi muốn tự động kiểm tra schema, duplicate, missing values, giá và volume bất hợp lệ, để chỉ dữ liệu đạt quality gate được chuyển sang mô hình.

**Priority:** P0  
**Owner:** MINHANH  
**Requirement trace:** PR-DAT-005–010, GATE-02.

**Output:** Data Quality Report, issue counts, pass/fail và affected tickers/dates.

## US-DAT-003 — Ngăn temporal leakage

**User Story**  
Với tư cách là Model Validator, tôi muốn xác nhận mọi feature tại ngày `t` chỉ sử dụng dữ liệu đến `t`, để backtest và recommendation không nhìn thấy tương lai.

**Priority:** P0  
**Owner:** MINHANH/TÚ  
**Requirement trace:** PR-DAT-011–014.

**Output:** temporal-integrity test evidence và data split manifest.

**Ngoại lệ:** Phát hiện leakage phải dừng model run và phát hành `ERR_DATA_TEMPORAL_LEAKAGE`.

## US-DAT-004 — Xem eligibility tại ngày đánh giá

**User Story**  
Với tư cách là Portfolio User, tôi muốn biết mã nào đủ điều kiện, mã nào bị loại và lý do, để hiểu phạm vi tài sản thực tế mà hệ thống đã phân tích.

**Priority:** P1  
**Owner:** MINHANH  
**Requirement trace:** PR-DAT-015–020.

**Main flow:** Eligibility Engine kiểm tra minimum history, data coverage, listing status và liquidity tại evaluation date.

**Output:** eligible pool, excluded tickers, reason codes và coverage summary.

## US-DAT-005 — Không tạo dữ liệu trước niêm yết

**User Story**  
Với tư cách là Model Validator, tôi muốn hệ thống loại một mã chưa có lịch sử thay vì nội suy ngược về trước ngày niêm yết, để tránh tạo dữ liệu giả và survivorship distortion bổ sung.

**Priority:** P0  
**Owner:** MINHANH  
**Requirement trace:** PR-DAT-016–018.

**Output:** exclusion reason `INSUFFICIENT_HISTORY` hoặc `NOT_LISTED_AT_DATE`.

## US-DAT-006 — Truy xuất nguồn và phiên bản dữ liệu

**User Story**  
Với tư cách là Judge/Model Validator, tôi muốn biết nguồn, ngày cập nhật, phiên bản và phạm vi dữ liệu của từng run, để có thể kiểm chứng và tái lập kết quả.

**Priority:** P1  
**Owner:** MINHANH  
**Requirement trace:** PR-DAT-009–010, PR-AUD-002–005.

---

# 6. EPIC-03 — MARKET REGIME DETECTION

## US-REG-001 — Xem trạng thái thị trường hiện tại

**User Story**  
Với tư cách là Portfolio User, tôi muốn biết thị trường đang bình thường, biến động hay stress, để hiểu bối cảnh của khuyến nghị giảm rủi ro.

**Priority:** P1  
**Owner:** TÚ  
**Requirement trace:** PR-REG-008–013, PR-UI-002.

**Output:** selected state, economic label, probabilities và evaluation date.

## US-REG-002 — Xem xác suất thay vì nhãn cứng

**User Story**  
Với tư cách là Portfolio User, tôi muốn xem xác suất của từng trạng thái, để hiểu mức độ chắc chắn thay vì tin tuyệt đối vào một nhãn duy nhất.

**Priority:** P0  
**Owner:** TÚ  
**Requirement trace:** PR-REG-010–013.

**Quy tắc:** Tổng xác suất bằng 1 trong tolerance; `p_stress` là probability của stress state.

## US-REG-003 — So sánh HMM 2–5 trạng thái

**User Story**  
Với tư cách là Model Validator, tôi muốn xem báo cáo so sánh HMM từ 2 đến 5 trạng thái qua nhiều seed, để xác nhận số trạng thái được chọn có bằng chứng chứ không bị áp đặt.

**Priority:** P0  
**Owner:** TÚ  
**Requirement trace:** PR-REG-001–007.

**Output:** log-likelihood, AIC, BIC, convergence, occupancy, stability và decision rationale.

## US-REG-004 — Diễn giải ý nghĩa kinh tế của state

**User Story**  
Với tư cách là Quant Risk Analyst, tôi muốn mỗi state có profile return, volatility và drawdown, để label normal/volatile/stress có cơ sở tài chính.

**Priority:** P1  
**Owner:** TÚ/PHÚC  
**Requirement trace:** PR-REG-008–009, PR-NFR-EXP-001.

## US-REG-005 — Fallback khi HMM không hội tụ

**User Story**  
Với tư cách là System Administrator, tôi muốn HMM failure kích hoạt fallback đã được phê duyệt hoặc dừng run rõ ràng, để không tạo state giả và tiếp tục pipeline âm thầm.

**Priority:** P0  
**Owner:** TÚ/TÂN  
**Requirement trace:** PR-REG-014–015, PR-OPS-007.

---

# 7. EPIC-04 — SCENARIO GENERATION

## US-SCN-001 — Sinh các kịch bản 20 ngày theo regime

**User Story**  
Với tư cách là Quant Risk Analyst, tôi muốn sinh nhiều đường đi lợi suất 20 ngày có điều kiện theo regime, để đo tail risk trong bối cảnh thị trường hiện tại.

**Priority:** P0  
**Owner:** TÚ  
**Requirement trace:** PR-SCN-001–008.

**Output:** scenario cube `[scenario, 20, asset]`, ticker order và scenario manifest.

## US-SCN-002 — Chọn số kịch bản phù hợp mục đích

**User Story**  
Với tư cách là Model Validator, tôi muốn dùng 2.000 scenarios cho development và 5.000 cho final evaluation, để cân bằng tài nguyên với độ ổn định của tail metrics.

**Priority:** P1  
**Owner:** TÚ/PHÚC  
**Requirement trace:** PR-SCN-002–003, PR-RSK-007–008.

## US-SCN-003 — Kiểm định scenario quality

**User Story**  
Với tư cách là Model Validator, tôi muốn kiểm tra moments, volatility, autocorrelation, cross-asset correlation và tail behavior, để biết scenarios có đủ tin cậy cho CVaR.

**Priority:** P0  
**Owner:** TÚ/PHÚC  
**Requirement trace:** PR-SCN-009–013.

**Output:** Scenario Validation Report và quality-gate status.

## US-SCN-004 — So sánh champion với CVAE challenger

**User Story**  
Với tư cách là AI/ML Owner, tôi muốn so sánh moving-block bootstrap với Conditional VAE trên cùng validation protocol, để chỉ thay champion khi challenger thực sự cải thiện.

**Priority:** P2  
**Owner:** TÚ  
**Requirement trace:** PR-SCN-014–015.

**Quy tắc:** CVAE failure không chặn core release; thay champion cần Decision Log approval.

## US-SCN-005 — Truy xuất cấu hình scenario

**User Story**  
Với tư cách là Judge/Model Validator, tôi muốn xem model version, block length, seed, conditioning regime và validation metrics, để tái lập đúng scenario set.

**Priority:** P1  
**Owner:** TÚ  
**Requirement trace:** PR-SCN-004–008, PR-AUD-003–005.

---

# 8. EPIC-05 — RISK VÀ CANDIDATE SELECTION

## US-RSK-001 — Xem tail risk trước phòng vệ

**User Story**  
Với tư cách là Portfolio User, tôi muốn xem CVaR 95%, 97,5%, 99%, VaR và drawdown của danh mục hiện tại, để hiểu quy mô tổn thất trong phần đuôi trước khi hành động.

**Priority:** P0  
**Owner:** PHÚC  
**Requirement trace:** PR-RSK-001–008, PR-UI-003.

**Output:** baseline risk report với units, confidence levels và scenario count.

## US-RSK-002 — Hiểu độ bất định của CVaR

**User Story**  
Với tư cách là Portfolio User, tôi muốn xem confidence interval và số tail observations, để không hiểu CVaR 99% là một con số chính xác tuyệt đối.

**Priority:** P1  
**Owner:** PHÚC  
**Requirement trace:** PR-RSK-007–008.

## US-RSK-003 — Xem breakdown chi phí và turnover

**User Story**  
Với tư cách là Portfolio User, tôi muốn xem phí, thuế, slippage, turnover và liquidity penalty, để đánh giá phương án có thực tế sau chi phí hay không.

**Priority:** P0  
**Owner:** PHÚC  
**Requirement trace:** PR-RSK-009–013.

## US-CAN-001 — Chọn động top 10 ứng viên

**User Story**  
Với tư cách là Portfolio User, tôi muốn hệ thống chọn 10 vị thế có tiềm năng giảm tail risk tốt nhất tại ngày đánh giá, để Quantum tập trung vào phần quyết định có giá trị cao.

**Priority:** P0  
**Owner:** PHÚC  
**Requirement trace:** PR-CAN-001–008.

**Output:** ordered candidate list và `candidate_order.json`.

## US-CAN-002 — Hiểu vì sao một mã được chọn

**User Story**  
Với tư cách là Portfolio User, tôi muốn xem marginal CVaR reduction, cost và liquidity penalty của từng mã, để hiểu candidate score thay vì nhận một danh sách hộp đen.

**Priority:** P1  
**Owner:** PHÚC  
**Requirement trace:** PR-CAN-001–004, PR-NFR-EXP-002.

## US-CAN-003 — Kiểm tra top-10 risk coverage

**User Story**  
Với tư cách là Model Validator, tôi muốn đo top-10 risk coverage, để biết việc thu hẹp từ 30 xuống 10 mã có bỏ sót quá nhiều rủi ro hay không.

**Priority:** P0  
**Owner:** PHÚC  
**Requirement trace:** PR-CAN-009–011.

**Ngoại lệ:** Coverage thấp tạo warning và sensitivity top 12/15; không âm thầm đổi QUBO baseline.

## US-CAN-004 — Chuyển xác suất stress thành ngân sách tiền mặt

**User Story**  
Với tư cách là Portfolio User, tôi muốn target cash budget tăng theo xác suất stress đã được hiệu chỉnh, để mức phòng vệ phản ánh bối cảnh thị trường một cách nhất quán.

**Priority:** P0  
**Owner:** TÚ/PHÚC  
**Requirement trace:** PR-CAN-012–015.

**Quy tắc:** Mapping đơn điệu; chỉ calibration trên validation 2023; threshold và budget thuộc Config Registry.

---

# 9. EPIC-06 — QUANTUM OPTIMIZATION

## US-QNT-001 — Nhận hành động 0/10/20/30% cho top 10

**User Story**  
Với tư cách là Portfolio User, tôi muốn Quantum lựa chọn mức giữ nguyên hoặc giảm 10%, 20%, 30% cho từng cổ phiếu top 10, để nhận một tổ hợp active set và coarse sizing có xét tương tác giữa các quyết định.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-QUB-001–005, PR-SLV-005–011.

**Output:** 20-bit solution, ticker mapping và decoded Quantum actions.

## US-QNT-002 — Xem và kiểm chứng bit mapping

**User Story**  
Với tư cách là Model Validator, tôi muốn xem candidate order và mapping `00/10/01/11`, để xác nhận bitstring được decode đúng ticker và đúng mức giảm.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-QUB-001–005.

**Quy tắc:** Sort bảng trên UI không được làm đổi mapping.

## US-QNT-003 — Xây QUBO từ financial evaluations thật

**User Story**  
Với tư cách là Quant Risk Analyst, tôi muốn QUBO surrogate được fit từ objective samples do Risk Engine tính, để Quantum tối ưu một xấp xỉ có liên hệ trực tiếp với bài toán tài chính.

**Priority:** P0  
**Owner:** PHÚC/TÂN  
**Requirement trace:** PR-QUB-006–012.

**Output:** 211+ structured samples, validation samples và versioned QUBO package.

## US-QNT-004 — Kiểm định QUBO surrogate trước khi chạy QAOA

**User Story**  
Với tư cách là Model Validator, tôi muốn xem prediction error, rank correlation, top-k recall và feasibility của surrogate, để không chạy QAOA trên một QUBO không phản ánh financial objective.

**Priority:** P0  
**Owner:** TÂN/PHÚC  
**Requirement trace:** PR-QUB-013–017.

**Ngoại lệ:** Surrogate fail phải dừng QAOA hợp lệ và phát hành `ERR_QUBO_SURROGATE_VALIDATION`.

## US-QNT-005 — Có nghiệm exact làm tham chiếu

**User Story**  
Với tư cách là Model Validator, tôi muốn exact solver tìm global optimum của QUBO 20-bit, để có mốc đánh giá chất lượng QAOA.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-SLV-001–004.

**Output:** exact best bitstring, energy, feasibility, runtime và QUBO hash.

## US-QNT-006 — Đánh giá QAOA qua nhiều seed

**User Story**  
Với tư cách là Model Validator, tôi muốn QAOA chạy trên danh sách seed đã đăng ký và báo cáo toàn bộ phân phối kết quả, để tránh cherry-pick một seed đẹp.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-SLV-005–011.

**Output:** per-seed metrics, aggregate distribution và sample probabilities.

## US-QNT-007 — So sánh Quantum, exact và classical công bằng

**User Story**  
Với tư cách là Judge/Model Validator, tôi muốn các solver dùng cùng QUBO hash và cùng constraint interpretation, để benchmark có ý nghĩa.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-SLV-012–014.

**Output:** best energy, optimality gap, feasible rate, optimum sampling probability, runtime và backend information.

## US-QNT-008 — Fallback khi QAOA không hoạt động

**User Story**  
Với tư cách là Portfolio User, tôi muốn hệ thống vẫn hoàn tất bằng exact/classical fallback khi QAOA timeout hoặc không sinh nghiệm hợp lệ, đồng thời ghi rõ solver thực tế, để không bị mất toàn bộ phân tích hoặc hiểu nhầm kết quả fallback là Quantum.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-SLV-015, PR-OPS-006.

---

# 10. EPIC-07 — TRUE RE-RANKING, POLISHING VÀ ACCOUNTING

## US-FIN-001 — Tính lại nghiệm Quantum bằng hàm tài chính thực

**User Story**  
Với tư cách là Quant Risk Analyst, tôi muốn tính lại CVaR và financial objective thực cho các bitstring tốt nhất, để không chọn final recommendation chỉ dựa trên QUBO energy xấp xỉ.

**Priority:** P0  
**Owner:** PHÚC  
**Requirement trace:** PR-FIN-001–006.

**Output:** true-objective ranking, surrogate-vs-true rank comparison và selected coarse candidate.

## US-FIN-002 — Tinh chỉnh cục bộ nhưng giữ vai trò Quantum

**User Story**  
Với tư cách là Portfolio User, tôi muốn mức giảm Quantum được tinh chỉnh tối đa ±5 điểm phần trăm trên active set đã chọn, để cải thiện financial objective mà không biến polishing thành một optimizer thay thế Quantum.

**Priority:** P0  
**Owner:** PHÚC/TÂN  
**Requirement trace:** PR-FIN-007–012.

**Quy tắc:** Quantum 0% phải giữ 0%; final reduction không vượt 30%.

## US-FIN-003 — Xem mức phụ thuộc vào polishing

**User Story**  
Với tư cách là Model Validator, tôi muốn đo phần cải thiện do Quantum và phần cải thiện do polishing, để đánh giá vai trò thực chất của Quantum.

**Priority:** P1  
**Owner:** PHÚC/TÂN  
**Requirement trace:** PR-FIN-011–012, PR-NFR-EXP-003.

## US-FIN-004 — Nhận danh mục sau giao dịch có accounting đúng

**User Story**  
Với tư cách là Portfolio User, tôi muốn giá trị bán, chi phí, tiền mặt và tỷ trọng cuối được đối soát, để phương án không tạo tỷ trọng âm hoặc tổng tỷ trọng khác 100%.

**Priority:** P0  
**Owner:** PHÚC/TÂN  
**Requirement trace:** PR-FIN-013–018.

**Output:** final portfolio, cash before/after, transaction cost và constraint status.

## US-FIN-005 — Nhận cảnh báo khi phương án không cải thiện CVaR

**User Story**  
Với tư cách là Portfolio User, tôi muốn hệ thống thông báo trung thực khi CVaR sau cao hơn hoặc không cải thiện đáng kể, để không hiểu một output hợp lệ về kỹ thuật là một khuyến nghị tốt về tài chính.

**Priority:** P0  
**Owner:** NGOC/PHÚC  
**Requirement trace:** PR-UI-017, PR-NFR-EXP-004.

## US-FIN-006 — Hiểu toàn bộ đánh đổi trước–sau

**User Story**  
Với tư cách là Portfolio User, tôi muốn so sánh CVaR, expected return, turnover, cost, cash và weights trước–sau, để quyết định liệu mức giảm rủi ro có xứng đáng với chi phí và phần lợi nhuận kỳ vọng bị hy sinh.

**Priority:** P0  
**Owner:** NGOC/PHÚC/TÂN  
**Requirement trace:** PR-UI-006–007, PR-UI-015.

---

# 11. EPIC-08 — DASHBOARD VÀ REPORTING

## US-UI-001 — Xem hành trình phân tích trên một dashboard thống nhất

**User Story**  
Với tư cách là Portfolio User, tôi muốn xem dữ liệu đầu vào, regime, risk, top 10, Quantum và final recommendation theo một flow rõ ràng, để hiểu kết quả mà không phải mở nhiều file kỹ thuật.

**Priority:** P1  
**Owner:** TÂN/NGOC  
**Requirement trace:** PR-UI-001–008.

## US-UI-002 — Phân biệt kết quả Quantum thô và kết quả cuối

**User Story**  
Với tư cách là Portfolio User, tôi muốn nhìn thấy riêng Quantum raw action và polished final action, để biết phần nào do Quantum quyết định và phần nào do hậu xử lý.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-UI-005–007, PR-NFR-UX-004.

## US-UI-003 — Truy xuất nguồn của mỗi số liệu

**User Story**  
Với tư cách là Model Validator, tôi muốn mỗi metric trên dashboard có run ID, unit và artifact source, để đối chiếu với backend và phát hiện số liệu viết tay.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-UI-009–013, PR-AUD-005.

## US-UI-004 — Xuất báo cáo đầy đủ

**User Story**  
Với tư cách là Portfolio User hoặc Judge, tôi muốn export báo cáo gồm assumptions, methodology, config, results, benchmark, warnings và limitations, để thẩm định hoặc trình bày kết quả ngoài dashboard.

**Priority:** P1  
**Owner:** NGOC/TÂN  
**Requirement trace:** PR-UI-014–018.

## US-UI-005 — Hiểu Q-SHIELD không tự đặt lệnh

**User Story**  
Với tư cách là Portfolio User, tôi muốn được thông báo rõ Q-SHIELD chỉ hỗ trợ quyết định và không tự động giao dịch, để không nhầm Proposed Action Plan với lệnh đã gửi ra thị trường.

**Priority:** P0  
**Owner:** NGOC  
**Requirement trace:** PR-UI-018, PR-OPS-009, PR-NFR-SEC-005.

## US-UI-006 — Sử dụng offline demo có nhãn rõ ràng

**User Story**  
Với tư cách là Judge hoặc người demo, tôi muốn xem một validated cached run khi môi trường tính toán không ổn định, để demo vẫn liền mạch nhưng không bị hiểu nhầm là dữ liệu thời gian thực.

**Priority:** P1  
**Owner:** TÂN  
**Requirement trace:** PR-OPS-001–003, PR-UI-013.

---

# 12. EPIC-09 — GOVERNANCE, AUDIT VÀ OPERATIONS

## US-GOV-001 — Phê duyệt cấu hình trước baseline

**User Story**  
Với tư cách là Product Owner, tôi muốn mọi tham số tài chính, dữ liệu, mô hình và Quantum được quản lý bằng Config Registry có version và người phê duyệt, để các module không tự dùng các giá trị khác nhau.

**Priority:** P0  
**Owner:** NGOC/TÂN  
**Requirement trace:** PR-CFG-001–006.

**Output:** approved config version/hash; development override được gắn `NON_BASELINE_RUN`.

## US-GOV-002 — Quản lý Data/Model/Financial/Quantum Registries

**User Story**  
Với tư cách là Model Validator, tôi muốn truy xuất phiên bản dữ liệu, mô hình, policy tài chính và QUBO/solver, để biết chính xác một run đã sử dụng thành phần nào.

**Priority:** P0  
**Owner:** MINHANH/TÚ/PHÚC/TÂN  
**Requirement trace:** PR-CFG-007–010.

## US-GOV-003 — Thực hiện change control

**User Story**  
Với tư cách là Product Owner, tôi muốn thay đổi lớn về universe, action grid, risk metric hoặc Quantum dimension phải qua Change Request, để tránh scope drift và incompatibility âm thầm.

**Priority:** P0  
**Owner:** NGOC  
**Requirement trace:** PR-CFG-011–013.

## US-AUD-001 — Tái lập một run

**User Story**  
Với tư cách là Model Validator, tôi muốn sử dụng run manifest, config, versions, seeds và environment để chạy lại một kết quả, nhằm xác nhận báo cáo có thể tái lập.

**Priority:** P0  
**Owner:** TÂN  
**Requirement trace:** PR-AUD-001–010.

## US-AUD-002 — Truy xuất requirement đến evidence

**User Story**  
Với tư cách là Product Owner, tôi muốn mỗi requirement và Acceptance Criteria liên kết với Test Case và artifact, để biết chính xác claim nào đã được kiểm chứng.

**Priority:** P0  
**Owner:** NGOC/PHÚC  
**Requirement trace:** PR-AUD-011–012.

## US-OPS-001 — Nhận lỗi có cấu trúc và hướng xử lý

**User Story**  
Với tư cách là System Administrator, tôi muốn lỗi có code, module, timestamp, retry rule và recommended action, để debug mà không phải suy đoán từ stack trace rời rạc.

**Priority:** P1  
**Owner:** TÂN  
**Requirement trace:** PR-OPS-004–007, Section 20 PRS.

## US-OPS-002 — Triển khai và chạy offline bằng runbook

**User Story**  
Với tư cách là thành viên ngoài module owner, tôi muốn cài đặt và chạy Q-SHIELD theo một runbook, để chứng minh sản phẩm không phụ thuộc duy nhất vào máy hoặc kiến thức cá nhân của một thành viên.

**Priority:** P1  
**Owner:** TÂN  
**Requirement trace:** PR-OPS-001–003, PR-OPS-008–010, PR-AUD-010.

## US-GOV-004 — Phê duyệt UAT và nội dung công bố

**User Story**  
Với tư cách là Product Owner, tôi muốn kiểm tra end-to-end flow, dashboard, report, disclaimer và limitations trước release, để bảo đảm sản phẩm giải đúng bài toán và không đưa ra claim vượt bằng chứng.

**Priority:** P0  
**Owner:** NGOC  
**Requirement trace:** GATE-10, PR-UI-017–018, PR-NFR-EXP-004–005.

---

# 13. ENABLER STORIES

Enabler Stories tạo nền kỹ thuật cho User Stories nhưng không được trình bày như giá trị người dùng độc lập.

| ID | Enabler Story | Owner | Priority | Product stories được hỗ trợ |
|---|---|---|---:|---|
| EN-DAT-001 | Xây versioned data pipeline và schema validation | MINHANH | P0 | US-DAT-001–006 |
| EN-REG-001 | Xây HMM training/model-selection pipeline | TÚ | P0 | US-REG-001–005 |
| EN-SCN-001 | Xây scenario generator và validation suite | TÚ | P0 | US-SCN-001–005 |
| EN-RSK-001 | Xây canonical Risk Engine và financial objective | PHÚC | P0 | US-RSK/CAN/FIN |
| EN-QUB-001 | Xây objective sampler và validated QUBO builder | TÂN/PHÚC | P0 | US-QNT-003–004 |
| EN-SLV-001 | Xây exact, classical và Warm-start QAOA adapters | TÂN | P0 | US-QNT-005–008 |
| EN-INT-001 | Xây artifact contracts và end-to-end orchestrator | TÂN | P0 | Toàn bộ journey |
| EN-QA-001 | Xây RTM, automated tests và quality-gate runner | PHÚC/NGOC | P0 | US-AUD-001–002, US-GOV-004 |
| EN-UI-001 | Xây artifact-driven Streamlit interface | TÂN | P1 | US-UI-001–006 |
| EN-OPS-001 | Đóng gói environment, cache và offline runbook | TÂN | P1 | US-OPS-002 |

---

# 14. STORY DEPENDENCY MATRIX

| Story group | Phụ thuộc trực tiếp | Bàn giao bắt buộc |
|---|---|---|
| US-RUN-* | Universe và input schema | Validated portfolio + run ID |
| US-DAT-* | Source/Universe Registry | Clean data + eligibility report |
| US-REG-* | Market features | Regime probabilities + model report |
| US-SCN-* | Regime output + asset returns | Scenario cube + validation report |
| US-RSK-* | Portfolio + scenarios | Baseline risk + objective engine |
| US-CAN-* | Risk/cost/liquidity | Candidate order + `B_t` |
| US-QNT-* | Candidate order + objective samples | QUBO + solver candidates |
| US-FIN-* | Solver candidates + scenarios | Final actions + final portfolio |
| US-UI-* | Validated run artifacts | Dashboard + export |
| US-GOV/AUD/OPS-* | Tất cả module | Approved release package |

---

# 15. RELEASE SLICES

## R1 — Core end-to-end release

Bao gồm toàn bộ P0/P1 story cần cho:

- Portfolio validation.
- Fixed universe và dynamic eligibility.
- HMM regime detection.
- Bootstrap scenario generation.
- CVaR và candidate selection.
- Stress-to-cash policy.
- 20-bit QUBO.
- Exact solver và Warm-start QAOA p=1.
- True re-ranking và bounded polishing.
- Accounting, dashboard, audit và UAT.

## R1.1 — Challenger và robustness

- Conditional VAE challenger.
- QAOA p=2.
- Extended top-12/top-15 sensitivity.
- Additional model robustness visualizations.

## Future backlog

- Historical point-in-time VN30 membership.
- Intraday/real-time data.
- Extended hedge instruments.
- Broker sandbox hoặc paper-trading integration.
- Quantum hardware experiments.

Future backlog không phải điều kiện nghiệm thu R1.

---

# 16. DEFINITION OF READY CHO USER STORY

Một story chỉ chuyển sang `READY` khi:

1. Có actor, capability và business value rõ ràng.
2. Có Product Requirement trace.
3. Có owner và reviewer.
4. Input/output schema có sẵn hoặc có mock contract.
5. Dependency và exception flow đã xác định.
6. Config cần thiết đã approved hoặc được gắn draft rõ ràng.
7. Acceptance Criteria có thể viết ở dạng Given–When–Then.
8. Không mâu thuẫn với Product Scope invariants.
9. Có thể ước lượng và hoàn thành trong một sprint; nếu không phải tách nhỏ.

---

# 17. DEFINITION OF DONE CHO USER STORY

Một story chỉ chuyển sang `ACCEPTED` khi:

1. Implementation đã hoàn tất và code review pass.
2. Unit/integration tests pass.
3. Acceptance Criteria pass và có evidence.
4. Artifact có run ID, version và owner.
5. Error/fallback flow đã được kiểm thử.
6. Dashboard/report nếu liên quan khớp artifact.
7. RTM đã cập nhật.
8. Không còn defect P0.
9. Reviewer ngoài module owner đã xác nhận.
10. Product Owner chấp nhận với các story có output cho người dùng.

---

# 18. BACKLOG SUMMARY

| Epic | Số Product Stories | P0/P1 core | P2/P3 |
|---|---:|---:|---:|
| EPIC-01 Portfolio & Run | 6 | 6 | 0 |
| EPIC-02 Data | 6 | 6 | 0 |
| EPIC-03 Regime | 5 | 5 | 0 |
| EPIC-04 Scenario | 5 | 4 | 1 |
| EPIC-05 Risk & Candidate | 7 | 7 | 0 |
| EPIC-06 Quantum | 8 | 8 | 0 |
| EPIC-07 Final Finance | 6 | 6 | 0 |
| EPIC-08 Dashboard | 6 | 6 | 0 |
| EPIC-09 Governance & Operations | 8 | 8 | 0 |
| **Tổng** | **57** | **56** | **1** |

Ngoài ra có 10 Enabler Stories hỗ trợ implementation.

---

# 19. MACHINE-READABLE BACKLOG SUMMARY

```yaml
document: QSHIELD-US-001
version: 1.0
status: baseline_candidate
parent_scope: QSHIELD-PSS-001-v1.0
parent_requirements: QSHIELD-PRS-001-v1.0

actors:
  - portfolio_user
  - product_owner
  - data_owner
  - ai_ml_owner
  - quant_risk_analyst
  - technical_quantum_owner
  - model_validator_judge

epics:
  EPIC-01: portfolio_and_run_management
  EPIC-02: data_universe_and_eligibility
  EPIC-03: market_regime_detection
  EPIC-04: scenario_generation
  EPIC-05: risk_and_candidate_selection
  EPIC-06: quantum_optimization
  EPIC-07: true_reranking_polishing_accounting
  EPIC-08: dashboard_and_reporting
  EPIC-09: governance_audit_operations

core_journey:
  - validate_portfolio
  - build_eligible_universe
  - detect_market_regime
  - generate_regime_conditioned_scenarios
  - measure_baseline_tail_risk
  - select_dynamic_top_10
  - map_stress_to_cash_budget
  - build_and_validate_qubo
  - solve_with_exact_classical_qaoa
  - rerank_with_true_financial_objective
  - polish_with_locked_active_set
  - reconcile_portfolio_accounting
  - present_and_archive_results

release_rules:
  quantum_candidates: 10
  total_bits: 20
  action_mapping:
    "00": 0.00
    "10": 0.10
    "01": 0.20
    "11": 0.30
  qaoa_primary_depth: 1
  exact_reference_states: 1048576
  final_selection: true_financial_objective
  zero_action_locked_during_polishing: true
  automatic_trading: false
```

---

# 20. PHÊ DUYỆT

| Vai trò | Họ tên | Trạng thái | Ngày |
|---|---|---|---|
| Product Owner | Nguyễn Thị Ánh Ngọc | Chờ phê duyệt | TBD |
| Data Owner | Nguyễn Đỗ Minh Anh | Chờ xác nhận | TBD |
| AI/ML Owner | Nguyễn Anh Tú | Chờ xác nhận | TBD |
| Quant Risk Owner | Liêu Hoài Phúc | Chờ xác nhận | TBD |
| Technical/Quantum Owner | Đỗ Ngọc Tân | Chờ xác nhận | TBD |

---

**Kết thúc tài liệu — QSHIELD-US-001 v1.0 Baseline Candidate**
