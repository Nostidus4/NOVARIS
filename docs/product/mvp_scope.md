---
document_id: QSHIELD-PSS-001
document_title: Q-SHIELD Product Scope Statement
document_version: 1.0
document_status: Baseline Candidate
product_name: Q-SHIELD
team_name: NOVARIS
document_owner: Nguyễn Thị Ánh Ngọc
technical_owner: Đỗ Ngọc Tân
reviewers:
  - Nguyễn Đỗ Minh Anh
  - Nguyễn Anh Tú
  - Liêu Hoài Phúc
language: vi-VN
intended_release: Production-oriented Competition Prototype
confidentiality: Internal Project Use
last_updated: 2026-08-02
---

# Q-SHIELD — PRODUCT SCOPE STATEMENT

## Tuyên bố phạm vi sản phẩm cho hệ thống Quantum–AI hỗ trợ quản trị tail risk danh mục cổ phiếu

**Đội dự án:** NOVARIS  
**Product Owner và Project Lead:** Nguyễn Thị Ánh Ngọc  
**Trạng thái tài liệu:** Baseline Candidate — chỉ chuyển thành Approved Baseline sau khi toàn đội duyệt Decision Log và Config Registry.  
**Mục đích sử dụng:** Làm nguồn sự thật thống nhất cho Product Requirements, User Stories, Data Contract, Financial Objective Specification, Quantum Design Specification, Test Plan, UAT và báo cáo kỹ thuật.

---

# 1. KIỂM SOÁT TÀI LIỆU

## 1.1. Mục đích tài liệu

Tài liệu này xác định ranh giới sản phẩm Q-SHIELD: sản phẩm giải quyết vấn đề gì, phục vụ ai, nhận dữ liệu nào, thực hiện chức năng nào, tạo đầu ra nào, không thực hiện nội dung nào, vận hành dưới các giả định và ràng buộc nào, và được xem là thành công khi đáp ứng các tiêu chí nào.

Product Scope Statement không thay thế tài liệu thiết kế chi tiết. Tài liệu này đóng vai trò cấp cao hơn để bảo đảm mọi thiết kế dữ liệu, tài chính, AI, Quantum, phần mềm và giao diện đều phục vụ cùng một bài toán.

## 1.2. Nguyên tắc sử dụng

- Mọi Product Requirement phải truy xuất được về ít nhất một mục tiêu hoặc một hạng mục trong phạm vi của tài liệu này.
- Mọi chức năng không có trong tài liệu này phải được xem là ngoài phạm vi cho đến khi có Change Request được phê duyệt.
- Giá trị định lượng có thể hiệu chỉnh phải nằm trong Config Registry, không được hard-code phân tán trong source code.
- Nếu tài liệu nghiệp vụ, source code, dashboard và báo cáo không thống nhất, phiên bản Product Scope đã được phê duyệt cùng Decision Log và Config Registry là căn cứ xử lý.
- Những trường được đánh dấu `TBD` chưa phải quyết định cuối và phải được khóa trước Product Baseline v1.0.

## 1.3. Lịch sử phiên bản

| Phiên bản | Trạng thái | Nội dung | Người chịu trách nhiệm |
|---|---|---|---|
| 0.x | Draft | Các ý tưởng và flow ban đầu | Toàn đội |
| 1.0 | Baseline Candidate | Chuẩn hóa phạm vi theo kiến trúc 30 mã → top 10 → Quantum coarse sizing → true-CVaR re-ranking → local polishing | Nguyễn Thị Ánh Ngọc |
| 1.0 Approved | Chưa phát hành | Chỉ phát hành sau khi khóa các mục `TBD` trong Config Registry | Product Owner |

## 1.4. Thẩm quyền phê duyệt

| Vai trò | Trách nhiệm trong phê duyệt phạm vi |
|---|---|
| Product Owner — Nguyễn Thị Ánh Ngọc | Phê duyệt bài toán, người dùng, giá trị, phạm vi, policy tài chính, nội dung trình bày và UAT |
| Data Owner — Nguyễn Đỗ Minh Anh | Xác nhận phạm vi universe, nguồn dữ liệu, thời gian, eligibility và data quality |
| AI/ML Owner — Nguyễn Anh Tú | Xác nhận phạm vi HMM, scenario generation, model selection và validation |
| Quant Risk Owner — Liêu Hoài Phúc | Xác nhận CVaR, candidate scoring, financial objective, constraints, re-ranking và polishing |
| Technical/Quantum Owner — Đỗ Ngọc Tân | Xác nhận kiến trúc, interface, QUBO, QAOA, exact benchmark, tích hợp, dashboard và vận hành |

---

# 2. TÓM TẮT ĐIỀU HÀNH

Q-SHIELD là một hệ thống hỗ trợ quyết định nhằm giảm tail risk cho danh mục cổ phiếu thuộc một universe cố định gồm 30 mã VN30 tại ngày snapshot đã được phê duyệt. Hệ thống hướng đến người quản lý danh mục không sử dụng công cụ phái sinh và chỉ cho phép phòng vệ bằng cách giảm một phần vị thế cổ phiếu rồi chuyển giá trị bán ròng sang tiền mặt.

Q-SHIELD kết hợp ba lớp kỹ thuật:

1. **AI/Statistical Learning:** Gaussian Hidden Markov Model nhận diện trạng thái thị trường và ước lượng xác suất stress; Scenario Engine sinh các kịch bản lợi suất 20 ngày có điều kiện theo trạng thái.
2. **Quantitative Finance:** Risk Engine đo lường CVaR, expected return, turnover, transaction cost, liquidity risk và đánh giá tác động của từng phương án giảm tỷ trọng.
3. **Quantum Optimization:** 10 cổ phiếu ứng viên được mã hóa bằng 20 biến nhị phân. Warm-start QAOA tìm tổ hợp mức giảm 0%, 10%, 20%, 30%; exact solver cung cấp nghiệm tham chiếu trên cùng QUBO.

Do QUBO chỉ là mô hình bậc hai xấp xỉ financial objective thực, Q-SHIELD không lấy QAOA energy làm kết quả cuối. Các nghiệm Quantum tốt nhất phải được Risk Engine tính lại true CVaR, tái xếp hạng và tinh chỉnh cục bộ trong phạm vi nghiêm ngặt. Quantum trực tiếp quyết định active set và coarse sizing; polishing không được kích hoạt một cổ phiếu mà Quantum đã chọn 0%.

Sản phẩm cuối là một production-oriented prototype có pipeline tái lập, Streamlit dashboard, bộ benchmark Quantum–classical, báo cáo kỹ thuật và đầy đủ artifact kiểm chứng. Sản phẩm không tự động giao dịch, không bảo đảm lợi nhuận và không tuyên bố quantum advantage khi chưa có bằng chứng.

---

# 3. BỐI CẢNH VÀ BÀI TOÁN SẢN PHẨM

## 3.1. Bối cảnh

Danh mục cổ phiếu thường được quản trị dựa trên lợi suất kỳ vọng và biến động trung bình. Tuy nhiên, trong các giai đoạn căng thẳng, phân phối lợi suất có thể xuất hiện đuôi dày, tương quan giữa các tài sản tăng mạnh và mức thua lỗ thực tế vượt xa điều kiện bình thường. Các chỉ tiêu như variance hoặc volatility có thể không thể hiện đầy đủ mức tổn thất trong phần đuôi phân phối.

Nhà đầu tư cá nhân hoặc người quản lý danh mục không sử dụng phái sinh thường chỉ có một số hành động khả thi: giữ nguyên, giảm từng phần vị thế và chuyển sang tiền mặt. Khi danh mục gồm nhiều cổ phiếu, việc xác định đồng thời mã nào cần giảm và giảm bao nhiêu trở thành bài toán tổ hợp. Nếu mỗi cổ phiếu có bốn hành động, chỉ riêng 10 cổ phiếu đã tạo ra:

\[
4^{10}=1.048.576
\]

phương án. Bài toán còn phải cân bằng giữa giảm CVaR, duy trì lợi nhuận kỳ vọng, hạn chế turnover, chi phí giao dịch, thanh khoản và mức tiền mặt mục tiêu.

## 3.2. Pain point trọng tâm

**PS-001 — Thiếu nhận diện trạng thái:** Người quản lý danh mục không có cơ chế định lượng nhất quán để xác định thị trường đang bình thường, biến động hay stress.

**PS-002 — Thiếu stress scenarios có cấu trúc:** Các giả định thủ công hoặc cú sốc đơn lẻ không phản ánh đầy đủ phụ thuộc thời gian, volatility clustering và tương quan chéo giữa tài sản.

**PS-003 — Không gian quyết định lớn:** Việc thử thủ công nhiều tổ hợp giảm vị thế không khả thi, khó tái lập và dễ phụ thuộc cảm tính.

**PS-004 — Đánh đổi đa mục tiêu:** Phương án giảm rủi ro mạnh nhất có thể tạo chi phí, turnover hoặc return sacrifice quá cao.

**PS-005 — Khoảng cách giữa mô hình và sản phẩm:** Nhiều mô hình nghiên cứu chỉ trả về metric, chưa tạo workflow có đầu vào, khuyến nghị, giải thích, benchmark và audit trail.

## 3.3. Phát biểu bài toán

Làm thế nào để nhận diện sớm trạng thái căng thẳng, mô phỏng các kịch bản bất lợi và tối ưu tổ hợp giảm vị thế trong danh mục cổ phiếu thuộc universe VN30, nhằm giúp người quản lý danh mục không sử dụng phái sinh giảm expected tail loss một cách có kiểm soát, minh bạch và có thể kiểm chứng?

---

# 4. TẦM NHÌN, GIÁ TRỊ VÀ MỤC TIÊU

## 4.1. Product vision

Xây dựng Q-SHIELD thành một lớp hỗ trợ quyết định phòng vệ tail risk, kết nối chặt chẽ giữa nhận diện trạng thái bằng AI, đo lường tài chính và tối ưu Quantum, trong đó mọi khuyến nghị đều có thể truy xuất về dữ liệu, mô hình, cấu hình, nghiệm tối ưu và bằng chứng kiểm định.

## 4.2. Giá trị mang lại

**VAL-001 — Nhận biết bối cảnh:** Cung cấp xác suất stress và trạng thái thị trường có diễn giải.

**VAL-002 — Định lượng tail risk:** Đo CVaR trước và sau phòng vệ trên tập kịch bản có cấu trúc.

**VAL-003 — Ra quyết định có hệ thống:** Chuyển bài toán lựa chọn và sizing thành tối ưu tổ hợp có ràng buộc.

**VAL-004 — Minh bạch đánh đổi:** Hiển thị đồng thời risk reduction, return sacrifice, turnover, transaction cost và cash allocation.

**VAL-005 — Kiểm chứng vai trò Quantum:** So sánh QAOA với exact solver và classical baseline trên cùng một QUBO.

**VAL-006 — Khả năng tái lập:** Mỗi kết quả có run ID, version, config, seed, log và artifact nguồn.

## 4.3. Mục tiêu sản phẩm

| ID | Mục tiêu | Kết quả mong đợi |
|---|---|---|
| OBJ-001 | Chuẩn hóa đầu vào danh mục | Danh mục hợp lệ, có ngày đánh giá, tỷ trọng, tiền mặt và universe mapping rõ ràng |
| OBJ-002 | Nhận diện trạng thái thị trường | Xác suất từng state và nhãn state tại ngày đánh giá |
| OBJ-003 | Sinh kịch bản stress | 2.000–5.000 kịch bản đa tài sản, horizon 20 ngày, có validation |
| OBJ-004 | Đo tail risk | CVaR 95% là chỉ tiêu chính; 97,5% và 99% là robustness metrics |
| OBJ-005 | Rút gọn không gian quyết định | Chọn động top 10 ứng viên từ universe 30 mã tại từng ngày đánh giá |
| OBJ-006 | Tối ưu Quantum có vai trò thực chất | Quantum quyết định cổ phiếu được tác động và coarse reduction 0/10/20/30% |
| OBJ-007 | Kiểm định nghiệm Quantum | Exact benchmark, true-CVaR re-ranking và limited polishing |
| OBJ-008 | Tạo sản phẩm sử dụng được | Dashboard, report, export, audit artifacts và offline demo |
| OBJ-009 | Bảo đảm quản trị mô hình | Không leakage, không cherry-pick seed và công bố limitations |

## 4.4. Mục tiêu không thuộc cam kết

Q-SHIELD không đặt mục tiêu dự báo chính xác giá từng cổ phiếu, tối đa hóa lợi nhuận tuyệt đối, thay thế nhà quản lý danh mục, hoặc chứng minh ưu thế lượng tử trên phần cứng lượng tử thực trong phiên bản này.

---

# 5. NGƯỜI DÙNG, BÊN LIÊN QUAN VÀ NHU CẦU

## 5.1. Người dùng chính

**USR-001 — Portfolio User:** Nhà đầu tư hoặc người quản lý danh mục đang nắm giữ các cổ phiếu thuộc universe đã chốt, không dùng phái sinh và cần đánh giá phương án chuyển một phần vị thế sang tiền mặt.

Nhu cầu chính:

- Nhập hoặc chọn danh mục và ngày đánh giá.
- Biết trạng thái thị trường và xác suất stress.
- Hiểu CVaR hiện tại và mức rủi ro trong các kịch bản bất lợi.
- Biết cổ phiếu nào được đưa vào top 10 và vì sao.
- Nhận phương án giảm tỷ trọng có giải thích.
- So sánh trước–sau và hiểu chi phí/đánh đổi.
- Xuất báo cáo để thẩm định hoặc trình bày.

## 5.2. Người dùng thứ cấp

**USR-002 — Product Owner:** Kiểm soát requirement, chính sách tài chính, tính nhất quán và UAT.

**USR-003 — Risk Analyst/Model Validator:** Kiểm tra CVaR, scenario quality, financial objective, QUBO surrogate và benchmark.

**USR-004 — System Administrator:** Quản lý data version, model version, configuration, run, cache và deployment.

**USR-005 — Giám khảo/người thẩm định:** Xem logic, bằng chứng, benchmark, hạn chế và khả năng tái lập.

## 5.3. Bên liên quan

| ID | Bên liên quan | Mối quan tâm |
|---|---|---|
| STK-001 | Đội NOVARIS | Hoàn thiện sản phẩm thống nhất, khả thi và bảo vệ được về học thuật |
| STK-002 | Ban Tổ chức cuộc thi | Mức độ ứng dụng, sáng tạo, tính khoa học và chất lượng prototype |
| STK-003 | Người dùng thử | Kết quả dễ hiểu, không gây hiểu nhầm và có giá trị hỗ trợ quyết định |
| STK-004 | Người đánh giá kỹ thuật | Pipeline đúng, không leakage, benchmark công bằng và artifact đầy đủ |

---

# 6. PHẠM VI NGHIỆP VỤ

## 6.1. Hành trình người dùng trong phạm vi

| ID | Giai đoạn | Nội dung trong phạm vi |
|---|---|---|
| BUS-001 | Chuẩn bị | Chọn ngày đánh giá, danh mục, tỷ trọng tiền mặt và cấu hình risk level |
| BUS-002 | Xác thực | Kiểm tra ticker, tỷ trọng, universe, eligibility, data coverage và liquidity |
| BUS-003 | Phân tích trạng thái | Ước lượng xác suất state và xác suất stress |
| BUS-004 | Mô phỏng | Sinh scenario paths 20 ngày theo state hiện tại |
| BUS-005 | Đo rủi ro | Tính CVaR, VaR, expected return, drawdown và confidence interval |
| BUS-006 | Rút gọn | Chọn top 10 cổ phiếu có giá trị phòng vệ tiềm năng cao |
| BUS-007 | Tối ưu | Mã hóa 20 bit và giải QUBO bằng exact solver, QAOA và baseline |
| BUS-008 | Kiểm định | Re-rank bằng true financial objective và local polishing có giới hạn |
| BUS-009 | Trình bày | Dashboard trước–sau, giải thích, benchmark, cảnh báo và export |
| BUS-010 | Kiểm toán | Lưu run manifest, config, versions, seeds, logs và artifacts |

## 6.2. Quyết định được hỗ trợ

Q-SHIELD hỗ trợ trả lời năm câu hỏi:

1. Thị trường tại ngày đánh giá đang thuộc trạng thái nào và xác suất stress là bao nhiêu?
2. Danh mục hiện tại có tail risk ở mức nào theo CVaR?
3. Những cổ phiếu nào đóng góp đáng kể vào tail risk và có hiệu quả giảm rủi ro sau khi xét chi phí?
4. Với top 10 ứng viên, tổ hợp mức giảm 0%, 10%, 20%, 30% nào cân bằng tốt nhất các mục tiêu?
5. Sau kiểm định bằng hàm tài chính thực, danh mục và tiền mặt thay đổi như thế nào?

## 6.3. Quyết định không được tự động hóa

- Q-SHIELD không tự quyết định có thực hiện giao dịch ngoài sự chấp thuận của người dùng.
- Q-SHIELD không gửi lệnh đến công ty chứng khoán.
- Q-SHIELD không tự thay đổi risk appetite, cash budget hoặc giới hạn tài chính.
- Q-SHIELD không tự cập nhật Config Registry đang ở trạng thái Approved.

---

# 7. PHẠM VI CHỨC NĂNG

## 7.1. Portfolio Intake và Validation

**FUNC-001:** Cho phép nhập danh mục gồm ticker, tỷ trọng hoặc giá trị vị thế, tiền mặt và ngày đánh giá.

**FUNC-002:** Kiểm tra ticker trùng, ticker ngoài universe, tỷ trọng âm, dữ liệu thiếu, tổng tỷ trọng và định dạng ngày.

**FUNC-003:** Gắn mỗi yêu cầu hợp lệ với một `run_id` duy nhất.

**FUNC-004:** Không tự động sửa hoặc chuẩn hóa đầu vào không hợp lệ mà không thông báo cho người dùng.

**FUNC-005:** Phiên bản cơ sở yêu cầu ít nhất 10 cổ phiếu đang có tỷ trọng dương và đủ eligibility để chạy cấu hình Quantum 20 bit. Nếu có ít hơn 10, hệ thống vẫn có thể trả risk analysis nhưng không phát hành Quantum recommendation 20 bit; trạng thái phải được gắn nhãn `INSUFFICIENT_QUANTUM_CANDIDATES`.

## 7.2. Universe và Eligibility

**FUNC-006:** Quản lý một master universe gồm 30 mã VN30 được cố định tại ngày snapshot trong Universe Registry.

**FUNC-007:** Tại mỗi ngày đánh giá, tính eligibility động dựa trên lịch sử tối thiểu, data coverage, trạng thái niêm yết và thanh khoản.

**FUNC-008:** Chỉ các mã vừa có tỷ trọng dương trong danh mục vừa đạt eligibility mới được xem là ứng viên giảm vị thế.

**FUNC-009:** Lưu mã bị loại và lý do loại trong artifact.

**FUNC-010:** Công bố rằng việc dùng danh sách 30 mã hiện tại để hồi cứu tạo survivorship bias; không trình bày kết quả như backtest trên historical point-in-time VN30 constituents.

## 7.3. Market Regime Engine

**FUNC-011:** Huấn luyện Gaussian HMM trên market-level features của giai đoạn train.

**FUNC-012:** Thử cấu hình 2–5 trạng thái; đánh giá bằng AIC, BIC, convergence, stability, state occupancy và khả năng diễn giải kinh tế.

**FUNC-013:** Ba trạng thái là giả thuyết kỳ vọng, không phải số trạng thái bị ép cố định nếu bằng chứng validation không ủng hộ.

**FUNC-014:** Xuất state probabilities, selected state, state label, model version và uncertainty information.

**FUNC-015:** Không được dùng dữ liệu test để chọn số trạng thái, feature, seed hoặc policy.

## 7.4. Scenario Engine

**FUNC-016:** Sử dụng regime-conditioned moving-block bootstrap làm champion model.

**FUNC-017:** Conditional VAE là challenger model; thất bại của CVAE không chặn release nếu champion đạt acceptance criteria.

**FUNC-018:** Sinh 2.000 scenario paths cho development và 5.000 paths cho final evaluation; mỗi path dài 20 ngày giao dịch.

**FUNC-019:** Thử block length 3, 5, 10 hoặc tập giá trị được Config Registry phê duyệt.

**FUNC-020:** Kiểm tra scenario shape, missing values, moments, volatility, cross-asset correlation, tail behavior và regime consistency.

**FUNC-021:** Lưu seed, model version, conditioning regime, block length và validation metrics.

## 7.5. Risk Engine

**FUNC-022:** Tính portfolio return và loss nhất quán theo sign convention `loss = -return`.

**FUNC-023:** Tính CVaR 95% làm primary risk metric; CVaR 97,5% và 99% làm robustness metrics.

**FUNC-024:** Tính confidence interval; cảnh báo số quan sát đuôi thấp đối với CVaR 99%.

**FUNC-025:** Tính VaR, expected return, maximum drawdown, turnover, transaction cost, liquidity penalty và cash generated.

**FUNC-026:** Tính risk contribution hoặc marginal CVaR reduction cho từng tài sản đủ điều kiện.

**FUNC-027:** Bảo đảm một financial objective duy nhất được sử dụng cho objective sampling, re-ranking, polishing, dashboard và báo cáo.

## 7.6. Top-10 Candidate Selection

**FUNC-028:** Chọn động 10 ứng viên tại mỗi evaluation date từ các vị thế đủ điều kiện.

**FUNC-029:** Candidate score phải kết hợp marginal CVaR reduction, transaction cost và illiquidity penalty theo công thức được phê duyệt.

**FUNC-030:** Thứ tự tie-break phải xác định trước và có tính deterministic.

**FUNC-031:** Tính top-10 risk coverage; nếu thấp hơn threshold phải cảnh báo và cung cấp sensitivity top 12 hoặc top 15 ở chế độ phân tích.

**FUNC-032:** Chế độ sensitivity không được âm thầm thay đổi QUBO dimension chính thức của một run 20 bit.

## 7.7. Stress-to-Cash Policy

**FUNC-033:** Ánh xạ xác suất stress `p_stress` thành target cash budget `B_t`.

**FUNC-034:** Mapping phải đơn điệu: xác suất stress cao hơn không được tạo target cash budget thấp hơn.

**FUNC-035:** Threshold và budget chỉ được hiệu chỉnh trên train/validation; test set chỉ dùng đánh giá cuối.

**FUNC-036:** `B_t` được hiểu là mục tiêu tăng tỷ trọng tiền mặt có tolerance và penalty; giới hạn hard cap phải được xác định trong Config Registry.

## 7.8. Quantum Action Encoding

**FUNC-037:** Mỗi cổ phiếu top 10 được gán hai biến nhị phân.

**FUNC-038:** Ánh xạ hành động:

- `00` → giảm 0% vị thế hiện tại.
- `10` → giảm 10% vị thế hiện tại.
- `01` → giảm 20% vị thế hiện tại.
- `11` → giảm 30% vị thế hiện tại.

**FUNC-039:** Với 10 cổ phiếu, bitstring phải có đúng 20 bit.

**FUNC-040:** `candidate_order.json` là căn cứ duy nhất để decode bitstring; thay đổi thứ tự hiển thị không được thay đổi mapping.

**FUNC-041:** Hành động là tỷ lệ phần trăm của vị thế hiện tại, không phải số điểm phần trăm trực tiếp của NAV.

## 7.9. Financial Objective và QUBO Surrogate

**FUNC-042:** Financial objective phải phản ánh CVaR, expected return/return sacrifice, transaction cost, turnover, liquidity và cash-budget deviation theo trọng số được phê duyệt.

**FUNC-043:** Các thành phần objective phải được chuẩn hóa hoặc scale có căn cứ để tránh một thành phần chi phối chỉ do khác đơn vị.

**FUNC-044:** Risk Engine sinh tối thiểu 211 structured objective evaluations gồm intercept, 20 main effects và 190 pairwise effects.

**FUNC-045:** Bổ sung 500–2.000 validation/random samples theo nguồn lực và Config Registry.

**FUNC-046:** Fit quadratic surrogate và báo cáo prediction error, rank correlation, top-k recall, feasibility và stability.

**FUNC-047:** QAOA không được chạy trên surrogate không đạt validation threshold; hệ thống phải phát hành lỗi rõ ràng thay vì tạo khuyến nghị giả.

## 7.10. Solvers và Benchmark

**FUNC-048:** Exact solver đánh giá đầy đủ `2^20 = 1.048.576` bitstrings hoặc dùng phương pháp exact tương đương có bằng chứng không bỏ sót nghiệm.

**FUNC-049:** Warm-start QAOA `p=1` là quantum configuration chính; `p=2` là challenger.

**FUNC-050:** QAOA sử dụng 1.024 shots và tối thiểu 10 random seeds trừ khi Config Registry được phê duyệt khác.

**FUNC-051:** Exact, QAOA và classical baseline phải sử dụng cùng QUBO hash, candidate order, action mapping và constraints.

**FUNC-052:** Benchmark phải báo cáo feasible rate, best energy, optimality gap, probability of sampling optimum, runtime, shots, seeds, depth và backend.

**FUNC-053:** Không cherry-pick seed; phải báo cáo phân phối kết quả trên toàn bộ seed đã đăng ký.

**FUNC-054:** Nếu QAOA timeout hoặc không có nghiệm hợp lệ, sử dụng exact/classical fallback và gắn nhãn solver thực tế.

## 7.11. True-Objective Re-ranking

**FUNC-055:** Chọn top 10–20 distinct feasible bitstrings từ QAOA/exact/classical candidate pool.

**FUNC-056:** Risk Engine tính lại true CVaR và toàn bộ financial objective cho từng bitstring.

**FUNC-057:** Phương án cuối không được chọn trực tiếp chỉ dựa trên QUBO energy.

**FUNC-058:** Báo cáo sự khác biệt giữa surrogate ranking và true-objective ranking.

## 7.12. Local Polishing

**FUNC-059:** Polishing chỉ hoạt động trên active set do Quantum chọn.

**FUNC-060:** Nếu Quantum action bằng 0%, final action bắt buộc bằng 0%.

**FUNC-061:** Với action khác 0%, polishing chỉ điều chỉnh tối đa ±5 điểm phần trăm và final action không vượt 30%.

**FUNC-062:** Lưu quantum action, polished action, adjustment và improvement sau polishing.

**FUNC-063:** Đo polishing dependency; nếu phần lớn hiệu quả chỉ xuất hiện sau polishing, phải công bố và xem lại surrogate/encoding.

## 7.13. Portfolio Accounting

**FUNC-064:** Giá trị bán của tài sản `i` được tính bằng giá trị vị thế hiện tại nhân mức giảm.

**FUNC-065:** Tiền bán ròng sau transaction cost được chuyển sang cash.

**FUNC-066:** NAV sau giao dịch bằng NAV trước giao dịch trừ chi phí; tỷ trọng sau giao dịch được tính trên NAV sau chi phí.

**FUNC-067:** Tổng tỷ trọng cổ phiếu và tiền mặt sau giao dịch phải bằng 100% trong tolerance.

**FUNC-068:** Không cho phép short selling, tỷ trọng âm hoặc mức giảm vượt giá trị vị thế.

## 7.14. Dashboard và Reporting

**FUNC-069:** Dashboard hiển thị portfolio input, evaluation date, data version và run status.

**FUNC-070:** Hiển thị state probabilities, stress probability và state interpretation.

**FUNC-071:** Hiển thị CVaR/VaR/drawdown trước và sau cùng confidence interval.

**FUNC-072:** Hiển thị top 10, candidate score components và risk coverage.

**FUNC-073:** Phân biệt Quantum raw action với polished final action.

**FUNC-074:** Hiển thị turnover, transaction cost, return sacrifice, cash before/after và constraint status.

**FUNC-075:** Hiển thị QAOA–exact–classical benchmark và solver thực tế đã được dùng.

**FUNC-076:** Mọi số liệu dashboard phải được đọc từ artifacts; dashboard không triển khai công thức tài chính độc lập.

**FUNC-077:** Cho phép export báo cáo và bảng hành động, kèm assumptions, config, limitations và disclaimer.

## 7.15. Auditability và Reproducibility

**FUNC-078:** Mỗi run có config, data version, model versions, seeds, package versions, logs và output manifest.

**FUNC-079:** Mỗi metric trình bày phải truy xuất được về artifact và script tạo ra nó.

**FUNC-080:** Mọi random process phải có seed hoặc danh sách seed được đăng ký.

**FUNC-081:** Một thành viên không phải module owner phải có khả năng chạy lại release candidate theo runbook.

---

# 8. PHẠM VI DỮ LIỆU

## 8.1. Universe

**DATA-001:** Master universe gồm 30 mã VN30 tại ngày snapshot được ghi trong Universe Registry.

**DATA-002:** Danh sách 30 mã được giữ cố định để bảo đảm scope và khả năng tái lập. Eligibility và top 10 thay đổi theo từng ngày đánh giá.

**DATA-003:** Mã chưa niêm yết hoặc chưa đủ lịch sử tại một thời điểm không được nội suy dữ liệu trước niêm yết.

## 8.2. Tần suất và trường dữ liệu

**DATA-004:** Tần suất chính là dữ liệu ngày.

**DATA-005:** Trường tối thiểu gồm date, ticker, adjusted close, volume, source và data version.

**DATA-006:** Feature có thể gồm market return, rolling volatility, drawdown, volume/liquidity proxy, cross-sectional dispersion và các biến đã được phê duyệt trong Model Specification.

## 8.3. Phân chia thời gian

| Layer | Train | Validation | Test |
|---|---|---|---|
| Market-level HMM | 2016–2022 | 2023 | 2024–30/06/2026 |
| Asset-level/scenario/risk layer | 02/07/2018–2022 | 2023 | 2024–30/06/2026 |

**DATA-007:** Giai đoạn 2016–2022 được dùng cho market-level features nếu dữ liệu chỉ số/thị trường đầy đủ.

**DATA-008:** Asset-level layer bắt đầu từ 02/07/2018 để tăng mức coverage giữa các mã trong universe đã chốt.

**DATA-009:** Validation 2023 dùng để chọn model, threshold, block length, stress policy và objective hyperparameters.

**DATA-010:** Test 2024–30/06/2026 chỉ dùng để báo cáo khả năng tổng quát hóa sau khi policy được khóa.

## 8.4. Data quality

**DATA-011:** Lịch sử tối thiểu mặc định 252 phiên tại ngày đánh giá.

**DATA-012:** Data coverage tối thiểu mặc định 98%, có thể thay đổi qua Config Registry.

**DATA-013:** Không forward-fill return qua giai đoạn chưa niêm yết hoặc đình chỉ kéo dài.

**DATA-014:** Corporate actions phải được xử lý qua adjusted price hoặc quy trình điều chỉnh được kiểm chứng.

**DATA-015:** Mỗi lần chạy tạo Data Quality Report và Eligibility Report.

## 8.5. Nguồn dữ liệu

Nguồn dữ liệu chính thức, quyền sử dụng, phương pháp tải và fallback source phải được ghi trong Source Registry. Tài liệu này không hard-code tên nhà cung cấp để tránh phụ thuộc vào một nguồn chưa được xác nhận về quyền truy cập và bản quyền.

---

# 9. PHẠM VI AI VÀ MÔ HÌNH THỐNG KÊ

## 9.1. Champion models

- Gaussian HMM cho market regime detection.
- Regime-conditioned moving-block bootstrap cho scenario generation.

## 9.2. Challenger models

- Gaussian HMM 2–5 states và các covariance structures.
- Conditional VAE cho scenario generation.
- Các mô hình nâng cao như Student-t HMM, HSMM, Markov-Switching GARCH hoặc change-point detection chỉ thuộc research backlog, trừ khi có Change Request đưa vào release.

## 9.3. Nguyên tắc model selection

- Không chọn model trên test set.
- Không dùng một metric duy nhất.
- Model phải hội tụ, ổn định, không tạo state quá nhỏ và có thể diễn giải.
- Challenger chỉ thay champion khi cải thiện có bằng chứng và không phá vỡ khả năng tích hợp.
- Model failure phải có fallback; không âm thầm thay đổi cấu hình.

## 9.4. Model outputs bắt buộc

- Model version và training window.
- Feature list và preprocessing version.
- State probabilities và labels.
- Selection metrics và stability report.
- Scenario manifest và validation metrics.
- Limitations và known failure modes.

---

# 10. PHẠM VI TÀI CHÍNH VÀ RỦI RO

## 10.1. Risk metric chính

CVaR 95% là chỉ tiêu ra quyết định chính. CVaR 97,5% và 99% dùng để kiểm tra độ bền, không được âm thầm thay thế objective chính sau khi xem test result.

Với loss scenarios `L_s`, CVaR được tính theo cùng một convention trong toàn hệ thống. Implementation chi tiết nằm trong Financial Objective Specification và phải có unit tests.

## 10.2. Financial objective

Financial objective cấp khái niệm:

\[
J(\mathbf d)=
\omega_1\,CVaR_{95\%}(\mathbf d)
-\omega_2\,E[R_p(\mathbf d)]
+\omega_3\,TC(\mathbf d)
+\omega_4\,Turnover(\mathbf d)
+\omega_5\,LiquidityPenalty(\mathbf d)
+\omega_6\,CashBudgetPenalty(\mathbf d).
\]

Trọng số, scale và đơn vị phải được phê duyệt trong Config Registry và Financial Objective Specification.

## 10.3. Hành động phòng vệ

- Giữ nguyên hoặc bán giảm 10%, 20%, 30% vị thế hiện tại.
- Không mua tăng tỷ trọng trong release này.
- Không short selling.
- Không sử dụng futures, options, ETF hedge, margin hoặc leverage.
- Tiền bán ròng được chuyển thành cash.

## 10.4. Transaction cost

Transaction cost có thể bao gồm phí giao dịch, thuế bán và slippage proxy. Giá trị và nguồn căn cứ phải nằm trong Config Registry. Không được dùng cùng một con số giả định cho mọi thử nghiệm mà không sensitivity analysis.

## 10.5. Accounting convention

Nếu NAV trước giao dịch là `V`, giá trị bán gộp là `S` và transaction cost là `TC`:

\[
V'=V-TC,
\]

\[
Cash'=Cash+S-TC.
\]

Tỷ trọng cuối được tính trên `V'`. Tổng tỷ trọng phải bằng 1 trong numerical tolerance.

---

# 11. PHẠM VI QUANTUM

## 11.1. Vai trò của Quantum

Quantum không chỉ bật/tắt ba hành động cố định. Với 20 biến, Quantum lựa chọn đồng thời:

- Active set: cổ phiếu nào trong top 10 cần giảm.
- Coarse position sizing: mức giảm 0%, 10%, 20% hoặc 30%.
- Tổ hợp đa tài sản có xét pairwise interactions trong QUBO.

## 11.2. QUBO representation

Với 20 biến nhị phân `z`, QUBO có dạng:

\[
\min_{\mathbf z\in\{0,1\}^{20}}
\mathbf z^\top Q\mathbf z+\mathbf q^\top\mathbf z+c.
\]

QUBO là quadratic surrogate của financial objective, không phải financial objective gốc. Vì vậy, surrogate validation và true-objective re-ranking là bắt buộc.

## 11.3. Quantum solver

- Warm-start QAOA `p=1` là cấu hình chính.
- `p=2` là challenger nếu tài nguyên cho phép.
- 1.024 shots và tối thiểu 10 seeds là baseline candidate.
- Simulator là môi trường thực thi chính của prototype.
- Quantum hardware là future option, không phải release dependency.

## 11.4. Exact benchmark

Exact solver trên 20 bits là nguồn sự thật để đánh giá QUBO-level optimality. Exact benchmark không xác nhận financial optimality nếu surrogate không tốt; vì vậy vẫn phải true-objective re-rank.

## 11.5. Tuyên bố được phép

Nhóm được phép tuyên bố:

- Đã biểu diễn bài toán coarse hedging dưới dạng QUBO.
- Đã chạy QAOA và so sánh trên cùng QUBO với exact/classical solver.
- Quantum tham gia trực tiếp vào active-set selection và coarse sizing.
- Đã kiểm định ảnh hưởng của surrogate và polishing.

Nhóm không được tuyên bố:

- Có quantum advantage nếu chưa chứng minh theo tiêu chuẩn tài nguyên và chất lượng nghiệm phù hợp.
- QAOA luôn tốt hơn exact/classical solver.
- Quantum tạo lợi nhuận hoặc loại bỏ hoàn toàn tail risk.

---

# 12. PHẠM VI PHẦN MỀM VÀ KIẾN TRÚC

## 12.1. Các module trong release

| ID | Module | Trách nhiệm |
|---|---|---|
| MOD-001 | Data Pipeline | Thu thập, chuẩn hóa, kiểm tra và version dữ liệu |
| MOD-002 | Eligibility Engine | Tạo eligible pool tại từng evaluation date |
| MOD-003 | HMM Engine | Ước lượng state probabilities và stress probability |
| MOD-004 | Scenario Engine | Sinh và kiểm định scenario cube |
| MOD-005 | Risk Engine | Tính metrics, financial objective và accounting |
| MOD-006 | Candidate Engine | Scoring và chọn top 10 |
| MOD-007 | Stress Policy Engine | Ánh xạ `p_stress` sang `B_t` |
| MOD-008 | Objective Sampler | Sinh structured/random financial evaluations |
| MOD-009 | QUBO Builder | Fit, validate và version quadratic surrogate |
| MOD-010 | Solver Layer | Exact, QAOA và classical baseline |
| MOD-011 | Re-ranking/Polishing | True-objective evaluation và limited refinement |
| MOD-012 | Artifact Store | Lưu config, models, outputs, logs và manifests |
| MOD-013 | Streamlit Dashboard | Trình bày và export kết quả |

## 12.2. Pipeline chuẩn

| Step ID | Bước | Input chính | Output chính |
|---|---|---|---|
| PIPE-01 | Validate portfolio | Portfolio request | Validated portfolio |
| PIPE-02 | Build eligible universe | Data + evaluation date | Eligibility report |
| PIPE-03 | Detect regime | Market features | State probabilities |
| PIPE-04 | Generate scenarios | State + asset returns | Scenario cube |
| PIPE-05 | Calculate baseline risk | Portfolio + scenarios | Baseline risk report |
| PIPE-06 | Select candidates | Risk/cost/liquidity | Ordered top 10 |
| PIPE-07 | Set cash budget | Stress probability | `B_t` |
| PIPE-08 | Sample objective | Candidate actions | Objective samples |
| PIPE-09 | Build QUBO | Samples + constraints | QUBO package |
| PIPE-10 | Solve | QUBO package | Exact/QAOA/classical candidates |
| PIPE-11 | Re-rank | Candidate bitstrings | True-objective ranking |
| PIPE-12 | Polish | Quantum active set | Final actions |
| PIPE-13 | Account and validate | Final actions | Final portfolio |
| PIPE-14 | Present and archive | Run artifacts | Dashboard/report/manifest |

## 12.3. Interface rule

- Module giao tiếp qua versioned artifacts hoặc typed interfaces.
- Không truyền dữ liệu bằng thao tác copy số thủ công.
- Mỗi artifact có schema, key, unit, null rule và producer/consumer.
- Thay đổi schema phải cập nhật Data Contract và regression tests.
- Dashboard là consumer của artifacts, không phải nguồn sự thật tính toán.

---

# 13. ĐẦU VÀO VÀ ĐẦU RA

## 13.1. Đầu vào người dùng

| ID | Đầu vào | Bắt buộc | Quy tắc |
|---|---|---:|---|
| IN-001 | Evaluation date | Có | Thuộc phạm vi dữ liệu hỗ trợ |
| IN-002 | Ticker và tỷ trọng/giá trị vị thế | Có | Ticker thuộc universe, vị thế không âm |
| IN-003 | Cash ban đầu | Có | Không âm |
| IN-004 | CVaR confidence view | Không | 95% mặc định; 97,5%/99% để kiểm tra độ bền |
| IN-005 | Run mode | Không | Development 2.000 hoặc Final 5.000 scenarios |

## 13.2. Đầu vào hệ thống

| ID | Đầu vào | Producer |
|---|---|---|
| IN-SYS-001 | Price, volume, corporate-action-adjusted fields | Data Pipeline |
| IN-SYS-002 | Market and asset features | Feature Pipeline |
| IN-SYS-003 | Approved configuration | Config Registry |
| IN-SYS-004 | Approved model artifacts | Model Registry |
| IN-SYS-005 | Cost/liquidity assumptions | Financial Policy Registry |

## 13.3. Đầu ra người dùng

| ID | Đầu ra | Nội dung tối thiểu |
|---|---|---|
| OUT-001 | Market State Panel | State probabilities, stress probability, interpretation |
| OUT-002 | Baseline Risk Panel | CVaR/VaR/drawdown/expected return trước phòng vệ |
| OUT-003 | Candidate Panel | Top 10, score components, risk coverage và lý do chọn |
| OUT-004 | Quantum Action Table | Ticker, bits, raw action, QAOA probability và constraint status |
| OUT-005 | Solver Benchmark | Exact/QAOA/classical quality, runtime và limitations |
| OUT-006 | Final Action Table | Quantum action, polished action, value sold và new weight |
| OUT-007 | Before–After Comparison | Risk, return, cost, turnover, cash và portfolio weights |
| OUT-008 | Exported Report | Assumptions, config, methodology, results, warnings, disclaimer |

## 13.4. Đầu ra kỹ thuật

| ID | Artifact |
|---|---|
| OUT-TECH-001 | `run_manifest.json` |
| OUT-TECH-002 | `portfolio_input.json` |
| OUT-TECH-003 | `data_version.json` và Data Quality Report |
| OUT-TECH-004 | `regime_daily.parquet` và Model Selection Report |
| OUT-TECH-005 | Scenario cube và `scenario_manifest.json` |
| OUT-TECH-006 | `risk_result.json` |
| OUT-TECH-007 | `candidate_order.json` và Candidate Coverage Report |
| OUT-TECH-008 | `objective_samples.parquet` |
| OUT-TECH-009 | `qubo.json` và Surrogate Validation Report |
| OUT-TECH-010 | Exact/QAOA/classical solver results |
| OUT-TECH-011 | True-objective re-ranking và polishing report |
| OUT-TECH-012 | `final_portfolio.json` |
| OUT-TECH-013 | `metrics.json`, `logs.txt` và environment manifest |

---

# 14. QUY TẮC NGHIỆP VỤ BẤT BIẾN

| ID | Quy tắc |
|---|---|
| BR-001 | Universe 30 mã là fixed snapshot; eligibility và top 10 là point-in-time dynamic |
| BR-002 | Không nội suy dữ liệu trước ngày niêm yết |
| BR-003 | Không dùng dữ liệu sau ngày đánh giá để tạo feature hoặc quyết định |
| BR-004 | CVaR 95% là primary metric |
| BR-005 | Chỉ vị thế dương và eligible mới được đưa vào hành động giảm |
| BR-006 | Action là 0%, 10%, 20%, 30% của vị thế hiện tại |
| BR-007 | Không mua tăng, không short, không leverage, không phái sinh |
| BR-008 | Mỗi mã top 10 có đúng hai bit; 10 mã tương ứng 20 bit |
| BR-009 | Bit mapping và candidate order được version theo từng run |
| BR-010 | Quantum quyết định active set và coarse sizing |
| BR-011 | Quantum action 0% không được polishing kích hoạt |
| BR-012 | Polishing tối đa ±5 điểm phần trăm và final reduction không vượt 30% |
| BR-013 | Mọi Quantum candidate phải được tính lại true financial objective |
| BR-014 | Exact và QAOA phải dùng cùng QUBO |
| BR-015 | Không cherry-pick seed |
| BR-016 | Transaction cost phải được trừ khi tính cash và NAV sau giao dịch |
| BR-017 | Tổng tỷ trọng sau giao dịch bằng 100% trong tolerance |
| BR-018 | Dashboard không có công thức tài chính riêng hoặc số liệu viết tay |
| BR-019 | Mọi output có run ID, version và artifact source |
| BR-020 | Không phát hành khuyến nghị nếu critical quality gate thất bại |

---

# 15. NGOÀI PHẠM VI

| ID | Hạng mục ngoài phạm vi release hiện tại | Lý do |
|---|---|---|
| OOS-001 | Tự động gửi hoặc thực thi lệnh giao dịch | Rủi ro vận hành, pháp lý và không cần thiết cho mục tiêu cuộc thi |
| OOS-002 | Dữ liệu intraday, tick hoặc order book | Chi phí dữ liệu và độ phức tạp vượt phạm vi |
| OOS-003 | Real-time streaming và cảnh báo liên tục | Release dùng batch daily/offline artifacts |
| OOS-004 | Futures, options, warrants hoặc phái sinh khác | Nhóm đã chốt cash-only mitigation |
| OOS-005 | Short selling, margin và leverage | Không phù hợp risk policy của release |
| OOS-006 | Mua tăng cổ phiếu hoặc tái cân bằng hai chiều toàn danh mục | Release chỉ tập trung de-risking bằng bán giảm |
| OOS-007 | Tối ưu danh mục dài hạn theo mean–variance hoặc asset allocation đầy đủ | Khác bài toán tail-risk mitigation |
| OOS-008 | Dự báo giá hoặc tín hiệu trading mua/bán ngắn hạn | Không phải product objective |
| OOS-009 | Historical point-in-time VN30 constituent reconstruction | Dữ liệu chưa nằm trong phạm vi; limitation phải công bố |
| OOS-010 | Quantum hardware là dependency bắt buộc | Simulator đủ cho benchmark prototype và dễ tái lập hơn |
| OOS-011 | Tuyên bố quantum advantage | Chưa có bằng chứng tài nguyên và chất lượng nghiệm đầy đủ |
| OOS-012 | Chatbot tư vấn đầu tư | Không đóng góp trực tiếp vào core value và tăng rủi ro nội dung |
| OOS-013 | Public multi-user authentication, billing và broker integration | Không cần cho competition prototype |
| OOS-014 | Cam kết hiệu quả đầu tư tương lai | Không phù hợp bản chất mô hình và quản trị rủi ro |

---

# 16. YÊU CẦU PHI CHỨC NĂNG

## 16.1. Tính đúng đắn

**NFR-001:** Công thức CVaR, transaction cost, turnover, accounting và bit decode có unit tests với expected values.

**NFR-002:** Các invariant như no-short, action bounds và total weights phải được kiểm tra tự động.

## 16.2. Khả năng tái lập

**NFR-003:** Exact path phải deterministic khi cùng input/config/version.

**NFR-004:** QAOA phải tái lập theo backend, package versions, shots và seed list đã lưu.

**NFR-005:** Mọi run có environment manifest hoặc lockfile.

## 16.3. Auditability

**NFR-006:** Mỗi số dashboard truy xuất được về artifact.

**NFR-007:** Mỗi artifact xác định producer, consumer, version và timestamp.

**NFR-008:** Thay đổi config approved phải tạo version mới và change reason.

## 16.4. Reliability

**NFR-009:** Critical module failure không được tạo output mang trạng thái thành công.

**NFR-010:** QAOA failure phải có fallback và disclosure.

**NFR-011:** Có offline demo sử dụng release artifacts đã kiểm chứng.

## 16.5. Hiệu năng

**NFR-012:** Dashboard sử dụng precomputed/cached artifacts để tương tác mượt; không chạy lại QAOA ở mọi thao tác UI.

**NFR-013:** Runtime end-to-end, peak memory và reference hardware phải được đo và báo cáo trước release. SLA định lượng được khóa sau benchmark, không tự đặt khi chưa có bằng chứng.

## 16.6. Usability

**NFR-014:** Giao diện phân biệt rõ input, model state, Quantum raw result, final result và limitations.

**NFR-015:** Mọi metric có nhãn, đơn vị và diễn giải ngắn.

**NFR-016:** Lỗi phải chỉ rõ nguyên nhân và hành động khắc phục; không hiển thị stack trace cho người dùng cuối.

## 16.7. Security và privacy

**NFR-017:** Release không yêu cầu dữ liệu định danh cá nhân.

**NFR-018:** File upload phải được kiểm tra định dạng, schema và kích thước.

**NFR-019:** Credential nguồn dữ liệu không được lưu trong source code, notebook, artifact hoặc repository.

**NFR-020:** Hệ thống không tự kết nối broker hoặc thực hiện giao dịch.

## 16.8. Maintainability

**NFR-021:** Data, model, risk, quantum và UI tách module rõ ràng.

**NFR-022:** Config tách khỏi code.

**NFR-023:** Interface thay đổi phải có version và regression test.

---

# 17. GIẢ ĐỊNH, RÀNG BUỘC VÀ PHỤ THUỘC

## 17.1. Giả định

| ID | Giả định |
|---|---|
| ASM-001 | Có thể thu thập dữ liệu giá và volume ngày hợp lệ cho phần lớn universe |
| ASM-002 | Portfolio input có ít nhất 10 vị thế dương, eligible để chạy 20-bit Quantum trong demo chính |
| ASM-003 | Người dùng chấp nhận cash-only là cơ chế giảm rủi ro của release |
| ASM-004 | Các proxy transaction cost và liquidity có thể được xây dựng từ dữ liệu khả dụng |
| ASM-005 | Máy phát triển có đủ RAM/CPU để chạy exact 20-bit QUBO và simulator với cấu hình được benchmark |
| ASM-006 | Các thành viên sử dụng chung schema, config và artifact contracts |

## 17.2. Ràng buộc

| ID | Ràng buộc |
|---|---|
| CON-001 | Universe chính gồm 30 mã; Quantum core sử dụng top 10 |
| CON-002 | Dữ liệu ngày; không intraday |
| CON-003 | Cash-only mitigation |
| CON-004 | Action grid 0/10/20/30% |
| CON-005 | 20 QUBO bits ở demo chính |
| CON-006 | Scenario horizon 20 ngày |
| CON-007 | CVaR 95% là primary metric |
| CON-008 | Test period không được dùng hiệu chỉnh |
| CON-009 | Simulator là quantum execution environment chính |
| CON-010 | Dashboard là decision-support, không phải trading execution system |

## 17.3. Phụ thuộc

| ID | Phụ thuộc | Owner | Ảnh hưởng nếu chưa có |
|---|---|---|---|
| DEP-001 | Approved Universe Registry | Minh Anh/Ngọc | Không khóa được data scope |
| DEP-002 | Data source và quyền sử dụng | Minh Anh | Không thể tái lập hoặc công bố dữ liệu |
| DEP-003 | Approved Config Registry | Ngọc/Tân | Các module dùng thông số khác nhau |
| DEP-004 | Data Contract | Minh Anh | Tích hợp module dễ lỗi schema/unit |
| DEP-005 | Financial Objective Specification | Phúc | Không thể sinh objective samples đúng |
| DEP-006 | QUBO Design Specification | Tân | Không thể benchmark solver công bằng |
| DEP-007 | Scenario Validation Report | Tú | Risk result thiếu căn cứ |
| DEP-008 | Test Plan và RTM | Ngọc/Phúc | Không chứng minh được requirement đã đạt |

---

# 18. RỦI RO SẢN PHẨM VÀ BIỆN PHÁP KIỂM SOÁT

| ID | Rủi ro | Ảnh hưởng | Kiểm soát |
|---|---|---|---|
| RSK-001 | Survivorship bias từ fixed current universe | Backtest có thể lạc quan | Công bố limitation; eligibility point-in-time; không gọi là historical VN30 universe |
| RSK-002 | Một số mã thiếu dữ liệu lịch sử | Giảm coverage | Không nội suy trước niêm yết; dùng asset start 02/07/2018; eligibility filter |
| RSK-003 | HMM state không ổn định | Narrative và scenario conditioning yếu | Multi-seed stability, occupancy, AIC/BIC, fallback baseline |
| RSK-004 | Scenario không giữ tail/correlation | CVaR không đáng tin | Validation battery, champion bootstrap, CVAE chỉ challenger |
| RSK-005 | CVaR 99% ít tail observations | CI rộng | 5.000 scenarios final, confidence interval, cảnh báo |
| RSK-006 | Top 10 không bao phủ đủ rủi ro | Quantum tối ưu sai vùng | Coverage metric và top-12/15 sensitivity |
| RSK-007 | Cost/slippage giả định yếu | Recommendation thiếu thực tế | Config source, sensitivity analysis và disclosure |
| RSK-008 | QUBO surrogate ranking kém | QAOA energy không phản ánh finance | Validation samples, ranking metrics, true-objective re-ranking |
| RSK-009 | QAOA simulator quá chậm | Demo gián đoạn | Cache results, p=1, giảm dev shots/seeds, exact fallback |
| RSK-010 | Polishing lấn át Quantum | Vai trò Quantum bị nhạt | Zero-lock, ±5pp bound, dependency metric |
| RSK-011 | Dashboard lệch backend | Trình bày sai kết quả | Artifact-only UI và reconciliation tests |
| RSK-012 | Scope creep | Không hoàn tất core | Change control; future items để ngoài release |
| RSK-013 | Hiểu nhầm là khuyến nghị đầu tư | Rủi ro đạo đức và pháp lý | Disclaimer, không execution, giải thích uncertainty |

---

# 19. TIÊU CHÍ THÀNH CÔNG

## 19.1. Tiêu chí bắt buộc để release

| ID | Tiêu chí | Cách đo |
|---|---|---|
| KPI-001 | Pipeline end-to-end hoàn tất | Portfolio input → final recommendation có run status `COMPLETED` |
| KPI-002 | Không leakage | Automated temporal tests và review đều pass |
| KPI-003 | Accounting đúng | No-short, action bounds, weights sum và cash reconciliation pass |
| KPI-004 | HMM có căn cứ | Selection/stability report được reviewer chấp nhận |
| KPI-005 | Scenarios hợp lệ | Scenario quality gate pass |
| KPI-006 | Top 10 minh bạch | Score components, order và coverage được lưu |
| KPI-007 | QUBO có validation | Surrogate metrics đạt threshold đã phê duyệt |
| KPI-008 | Benchmark công bằng | Exact/QAOA/classical dùng cùng QUBO hash |
| KPI-009 | Quantum candidates được true re-rank | Không có final recommendation chỉ dựa QUBO energy |
| KPI-010 | Polishing có kiểm soát | Zero-lock và ±5pp tests pass |
| KPI-011 | Dashboard khớp artifacts | Reconciliation tests pass |
| KPI-012 | Có khả năng tái lập | Thành viên khác chạy lại release theo runbook |
| KPI-013 | UAT đạt | Product Owner ký UAT Report |
| KPI-014 | Tuyên bố trung thực | Limitations, fallback và disclaimer được hiển thị |

## 19.2. Chỉ tiêu phân tích, không phải bảo đảm

Các metric sau được báo cáo nhưng không đặt trước như cam kết tuyệt đối:

- CVaR reduction trên test.
- Return sacrifice.
- Turnover và transaction cost.
- QAOA optimality gap.
- Probability of sampling exact optimum.
- Surrogate top-k recall.
- Top-10 risk coverage.
- Runtime và memory.

Ngưỡng đạt cho từng metric phải được khóa trước khi mở test result. Không được đặt ngưỡng sau khi xem kết quả để làm đẹp báo cáo.

---

# 20. BỘ SẢN PHẨM BÀN GIAO

| ID | Deliverable | Owner chính |
|---|---|---|
| DEL-001 | Product Scope Statement | Nguyễn Thị Ánh Ngọc |
| DEL-002 | User Stories, Product Requirements và Acceptance Criteria | Nguyễn Thị Ánh Ngọc |
| DEL-003 | Decision Log, Config Registry và RTM | Nguyễn Thị Ánh Ngọc/Đỗ Ngọc Tân |
| DEL-004 | Universe Registry, Source Registry và Data Contract | Nguyễn Đỗ Minh Anh |
| DEL-005 | Clean datasets, features, manifests và Data Quality Report | Nguyễn Đỗ Minh Anh |
| DEL-006 | HMM model, selection report và state outputs | Nguyễn Anh Tú |
| DEL-007 | Scenario Engine, scenario cube và validation report | Nguyễn Anh Tú |
| DEL-008 | Financial Objective Specification và Risk Engine | Liêu Hoài Phúc |
| DEL-009 | Candidate selection, coverage, cash policy và objective samples | Liêu Hoài Phúc |
| DEL-010 | QUBO Design, exact solver, QAOA và benchmark | Đỗ Ngọc Tân |
| DEL-011 | True-objective re-ranking và polishing report | Liêu Hoài Phúc/Đỗ Ngọc Tân |
| DEL-012 | Integrated pipeline và Streamlit dashboard | Đỗ Ngọc Tân |
| DEL-013 | Test Plan, test evidence, model validation và UAT | Phúc/Ngọc |
| DEL-014 | Technical Report, pitch deck, demo script và user manual | Nguyễn Thị Ánh Ngọc |
| DEL-015 | Deployment guide, offline package và final run manifest | Đỗ Ngọc Tân |

---

# 21. RELEASE VÀ TRIỂN KHAI

## 21.1. Release R1 — Core prototype

Bao gồm champion HMM, bootstrap scenarios, Risk Engine, dynamic top 10, 20-bit QUBO, exact solver, Warm-start QAOA p=1, true re-ranking, bounded polishing, dashboard và artifacts.

## 21.2. Release R1.1 — Challenger và robustness

Có thể bổ sung CVAE, QAOA p=2, extended sensitivity, additional plots và robustness analysis nếu R1 đã đạt quality gates.

## 21.3. Future production backlog

- Point-in-time historical VN30 membership.
- Licensed institutional data.
- Intraday monitoring.
- Paper trading và broker sandbox.
- Extended hedging instruments sau đánh giá pháp lý/dữ liệu.
- Cloud deployment, user authentication và monitoring.
- Quantum hardware experiments.

Future backlog không phải dependency để nghiệm thu R1.

---

# 22. QUẢN LÝ THAY ĐỔI PHẠM VI

## 22.1. Change Request bắt buộc khi

- Thêm hoặc loại một module core.
- Thay universe size hoặc Quantum candidate count.
- Thay action grid hoặc ý nghĩa action.
- Thay primary risk metric.
- Thêm phái sinh, short selling, mua tăng hoặc leverage.
- Thay data split hoặc sử dụng test để hiệu chỉnh.
- Thay vai trò Quantum trong quyết định cuối.
- Thay output cam kết với người dùng.

## 22.2. Nội dung Change Request

- Change ID và mô tả.
- Lý do nghiệp vụ/kỹ thuật.
- Requirement, schema, test và artifact bị ảnh hưởng.
- Tác động dữ liệu, model, tài chính, Quantum, dashboard và timeline.
- Rủi ro mới.
- Kế hoạch migration và rollback.
- Người đề xuất, reviewer và người phê duyệt.

## 22.3. Quy tắc version

- Thay đổi editorial không ảnh hưởng hành vi: tăng patch version.
- Thay đổi config/requirement tương thích: tăng minor version.
- Thay đổi action, universe logic, financial objective hoặc architecture không tương thích: tăng major version.

---

# 23. CÁC QUYẾT ĐỊNH CÒN MỞ

Các mục dưới đây không làm thay đổi kiến trúc, nhưng phải được khóa trước Approved Baseline:

| ID | Quyết định cần khóa | Owner đề xuất | Approver |
|---|---|---|---|
| TBD-001 | Danh sách chính xác 30 mã, snapshot date và nguồn | Minh Anh | Ánh Ngọc |
| TBD-002 | Transaction fee, sell tax, slippage model và liquidity proxy | Hoài Phúc | Ánh Ngọc |
| TBD-003 | Top-10 score weights và minimum risk coverage | Hoài Phúc | Ánh Ngọc |
| TBD-004 | `p_stress` thresholds, target cash budgets, hard cap và tolerance | Tú/Phúc | Ánh Ngọc |
| TBD-005 | Financial objective weights và scaling | Hoài Phúc | Ánh Ngọc |
| TBD-006 | QUBO regularization, penalty coefficients và surrogate thresholds | Ngọc Tân | Phúc/Ngọc |
| TBD-007 | Final QAOA seed list, optimizer, timeout và fallback thresholds | Ngọc Tân | Ánh Ngọc |
| TBD-008 | Numerical tolerances và performance SLA trên reference hardware | Tân/Phúc | Ánh Ngọc |
| TBD-009 | Nguồn dữ liệu cuối cùng và điều kiện bản quyền | Minh Anh | Ánh Ngọc |

Mỗi `TBD` phải được chuyển thành một mục trong Config Registry hoặc Decision Log, có giá trị, căn cứ, owner, approver, version và effective date.

---

# 24. ĐIỀU KIỆN PHÊ DUYỆT PRODUCT SCOPE

Product Scope Statement được chuyển từ `Baseline Candidate` sang `Approved` khi đáp ứng đầy đủ:

1. Toàn bộ năm thành viên xác nhận phạm vi module của mình.
2. Tất cả `TBD` critical đã được khóa hoặc có lý do defer được Product Owner chấp nhận.
3. Config Registry v1.0 được phê duyệt.
4. Decision Log phản ánh đầy đủ các quyết định kiến trúc và tài chính.
5. User Stories, Product Requirements và Acceptance Criteria sử dụng cùng ID và không mâu thuẫn với tài liệu này.
6. Data Contract, Financial Objective Specification và QUBO Design Specification đã có owner và reviewer.
7. RTM liên kết Scope → Requirement → Acceptance Criteria → Test Case → Evidence.
8. Product Owner ký Scope Approval.

---

# 25. TUYÊN BỐ GIỚI HẠN VÀ MIỄN TRỪ

Q-SHIELD là hệ thống hỗ trợ phân tích và ra quyết định dựa trên dữ liệu lịch sử, mô hình thống kê, mô phỏng và tối ưu. Kết quả phụ thuộc vào chất lượng dữ liệu, giả định chi phí, phương pháp sinh kịch bản, độ phù hợp của QUBO surrogate và cấu hình solver.

Q-SHIELD không phải khuyến nghị mua bán, không tự động thực hiện giao dịch, không bảo đảm giảm lỗ trong mọi điều kiện và không bảo đảm lợi nhuận. Cash-only mitigation có thể giảm exposure nhưng không loại bỏ hoàn toàn market risk, liquidity risk, gap risk hoặc model risk.

Việc sử dụng danh sách VN30 cố định tại ngày snapshot để hồi cứu có thể tạo survivorship bias. Kết quả phải được trình bày đúng là nghiên cứu trên fixed current-constituent universe, không phải historical point-in-time VN30 portfolio.

Kết quả QAOA phải được trình bày cùng exact/classical benchmark và không được diễn giải thành quantum advantage nếu chưa có bằng chứng phù hợp.

---

# 26. PHÊ DUYỆT

| Vai trò | Họ tên | Trạng thái | Ngày |
|---|---|---|---|
| Product Owner/Project Lead | Nguyễn Thị Ánh Ngọc | Chờ phê duyệt | TBD |
| Data Owner | Nguyễn Đỗ Minh Anh | Chờ xác nhận | TBD |
| AI/ML Owner | Nguyễn Anh Tú | Chờ xác nhận | TBD |
| Quant Risk Owner | Liêu Hoài Phúc | Chờ xác nhận | TBD |
| Technical/Quantum Owner | Đỗ Ngọc Tân | Chờ xác nhận | TBD |

---

# PHỤ LỤC A — MA TRẬN LIÊN KẾT CẤP CAO

| Scope Objective | Module | Output | Tiêu chí liên quan |
|---|---|---|---|
| OBJ-001 | MOD-001, MOD-002 | Validated portfolio, eligibility | KPI-001, KPI-002 |
| OBJ-002 | MOD-003 | State probabilities | KPI-004 |
| OBJ-003 | MOD-004 | Scenario cube | KPI-005 |
| OBJ-004 | MOD-005 | Risk report | KPI-003, KPI-009 |
| OBJ-005 | MOD-006 | Candidate order | KPI-006 |
| OBJ-006 | MOD-008–MOD-010 | QUBO và solver outputs | KPI-007, KPI-008 |
| OBJ-007 | MOD-011 | True ranking và final actions | KPI-009, KPI-010 |
| OBJ-008 | MOD-012, MOD-013 | Dashboard/report/manifest | KPI-011, KPI-012 |
| OBJ-009 | Tất cả | Validation, limitations, UAT | KPI-002, KPI-013, KPI-014 |

# PHỤ LỤC B — THỨ TỰ TÀI LIỆU NGUỒN SỰ THẬT

Khi có xung đột, áp dụng thứ tự ưu tiên sau:

1. Approved Product Scope Statement.
2. Approved Decision Log.
3. Approved Config Registry.
4. Approved Financial Objective Specification và Data Contract.
5. Product Requirements và Acceptance Criteria.
6. QUBO/Quantum Design Specification và Interface Contract.
7. Test Plan và UAT Plan.
8. Source code và run artifacts của release tương ứng.
9. Dashboard, slide và tài liệu trình bày.

Dashboard hoặc slide không được dùng để ghi đè quyết định đã được phê duyệt ở cấp cao hơn.

# PHỤ LỤC C — MACHINE-READABLE SCOPE SUMMARY

```yaml
product:
  name: Q-SHIELD
  type: production-oriented decision-support prototype
  domain: tail-risk mitigation for equity portfolios
  team: NOVARIS

users:
  primary: VN30 portfolio investor or manager without derivatives
  secondary:
    - product_owner
    - risk_analyst
    - model_validator
    - system_administrator
    - competition_judge

universe:
  type: fixed_snapshot
  size: 30
  family: VN30
  eligibility: dynamic_by_evaluation_date
  quantum_candidates: 10

data:
  frequency: daily
  market_train: 2016-01-01/2022-12-31
  asset_train: 2018-07-02/2022-12-31
  validation: 2023-01-01/2023-12-31
  test: 2024-01-01/2026-06-30

ai:
  regime_champion: Gaussian_HMM
  candidate_state_counts: [2, 3, 4, 5]
  scenario_champion: regime_conditioned_moving_block_bootstrap
  scenario_challenger: conditional_VAE
  scenario_counts:
    development: 2000
    final: 5000
  horizon_days: 20

finance:
  primary_metric: CVaR_95
  robustness_metrics: [CVaR_97_5, CVaR_99]
  hedge_instruments: [cash]
  action_semantics: percentage_of_current_position
  action_levels: [0.00, 0.10, 0.20, 0.30]
  short_selling: false
  buy_increase: false
  leverage: false

quantum:
  role:
    - active_set_selection
    - coarse_position_sizing
  bits_per_asset: 2
  total_bits: 20
  mapping:
    "00": 0.00
    "10": 0.10
    "01": 0.20
    "11": 0.30
  surrogate: validated_quadratic_QUBO
  reference_solver: exact_2_power_20
  primary_solver: warm_start_QAOA_p1
  challenger_solver: QAOA_p2
  shots: 1024
  minimum_seeds: 10
  final_selection: true_financial_objective_reranking
  polishing:
    active_set_locked: true
    maximum_adjustment_percentage_points: 5

delivery:
  interface: Streamlit_dashboard
  execution: offline_or_batch_daily
  automated_trading: false
  required_artifacts: true
  reproducible_runs: true

prohibited_claims:
  - guaranteed_profit
  - guaranteed_loss_prevention
  - automated_investment_advice
  - quantum_advantage_without_evidence
```

---

**Kết thúc tài liệu — QSHIELD-PSS-001 v1.0 Baseline Candidate**
