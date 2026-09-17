# NOVARIS: Quyết định đề xuất và phản hồi báo cáo 15/08

Ngày soạn: 31/08/2026 | Người duyệt cuối: Nguyễn Thị Ánh Ngọc.

**DRAFT_PENDING_NGOC_REVIEW. Đây là văn bản soạn để Ngọc review và gửi Tân, không phải biên bản đã ký.**

## 1. Kết luận nên gửi Tân

Ghi nhận đã chạy thử Data -> AI -> Risk -> Quantum và phát hiện các vấn đề có giá trị. Tuy nhiên chỉ chấp nhận kết quả này là **evidence phát triển/ANALYSIS_ONLY**, chưa nghiệm thu Workflow V2 và chưa công bố hiệu quả đầu tư hoặc quantum advantage.

Hướng đề xuất: sản phẩm hỗ trợ nhà đầu tư cá nhân đang giữ cổ phiếu giảm tail-risk bằng giảm vị thế và giữ tiền mặt; analyst/advisor có thể sử dụng hỗ trợ. Chưa tự đặt lệnh, chưa thêm futures vào release R1. Quantum là nhánh tạo ứng viên, không là điều kiện bắt buộc để trả một phương án classical hợp lệ.

Ưu tiên sửa tính tin cậy Data, độ phủ Stress và input danh mục thật trước khi tăng độ lớn QAOA. Có thể làm governance/API/UI và debug solver song song; mọi kết quả dùng dữ liệu chưa đạt vẫn là experimental.

## 2. Những điểm phải đính chính hoặc xác minh trong báo cáo

| ID | Vị trí PDF | Vấn đề | Phản hồi cần gửi |
|---|---|---|---|
| R01 | §3.3, §3.7, §11; tr.4–5,17 | 53/108 vi phạm lúc được nghi là pipeline, lúc quy hết vendor | Yêu cầu đối chiếu raw-vendor -> clean -> returns theo từng dòng, timestamp/timezone/reference/exchange. Chưa đủ cơ sở quy kết nguyên nhân. Không xóa dữ liệu chỉ vì giá hôm sau lặp lại. |
| R02 | §3.6–3.7; tr.5 | TCB 11/06/2024 ảnh hưởng lớn kurtosis, nhưng vẫn dùng return thô | Giữ nguyên raw cho audit; mở điều tra corporate action. Mã/ngày chưa xác minh không được lặng lẽ đi vào baseline. Không suy adjustment factor từ riêng cú nhảy giá. |
| R03 | §4.2; tr.6 | “Train” được mô tả bằng toàn feature frame tới 30/07/2026 | Xuất chính xác `fit_start/end`, `validation_start/end`, `test_start/end`, scaler-fit range. Frame dài bao nhiêu không chứng minh model fit trên khoảng đó. Audit filtered posterior vs smoothed/Viterbi trước khi kết luận không leakage. |
| R04 | §4.3–4.5; tr.6–7 | Stress bị skip, aggregate có chỗ gọi PASS/WARN | Gate cho full stress capability phải `INCOMPLETE/BLOCKED`; volatile PASS không đại diện cả 3 regime. Số scenario 5000 không bù được pool Stress rỗng. |
| R05 | §5.3, D6; tr.8,14 | Top-15 78,3% được gọi PASS dù stability chưa đánh giá | Chỉ là coverage component PASS. Candidate Gate tổng thể chưa PASS. Không tự đặt N=15 là đã giải quyết xong. |
| R06 | §5.4; tr.8 | Seed khác nhau được dùng để lý giải không overlap | Bằng chứng phải là hash/bitstring intersection bằng 0, không chỉ seed khác. Holdout phải chưa dùng để chọn encoding/hyperparameter. |
| R07 | §6.2, §6.6; tr.9–12 | Kết luận bug là race condition upstream, fallback “luôn đúng/không rủi ro” | Cần minimal reproducer, versions, trace và test trên process sạch. Stack trace chưa đủ chứng minh race condition; đúng circuit không đồng nghĩa QAOA tối ưu. Fallback vẫn có thể timeout/OOM; retry có overhead. |
| R08 | §6.3; tr.10–11 | So sánh 8/10-bit full settings với 20-bit dev settings để kết luận scaling chất lượng | Các instance/settings khác nhau: chỉ mô tả các kết quả đã đo, chưa phải thí nghiệm scaling có kiểm soát. Có số 10-bit thành công và thất bại ở các batch khác nhau, phải giữ đủ attempt logs. |
| R09 | §6.8d; tr.13 | Tăng 30–40 bit được xem là khiến classical khó và tạo cơ hội duy nhất cho Quantum | Số bit lớn không tự chứng minh hardness hoặc advantage. Không tăng N để tạo câu chuyện Quantum. 15 mã x 2 bit = 30 bit; statevector complex128 đơn thuần đã 16 GiB, chưa kể overhead. |
| R10 | §9; tr.16 | “7 workstream 0%” nhưng liệt kê 5 nhóm và trộn phần chưa làm với cả workstream | Thay % cảm tính bằng checklist deliverable và evidence. Phân biệt đã chạy, code tồn tại, test pass, gate pass, UAT pass. |
| R11 | §2–§6 | “Không giả lập” dễ bị hiểu là dùng QPU thật | Ghi “dữ liệu thị trường thật, chạy QAOA trên simulator”, không gọi QPU execution. |

**Không chấp nhận lập luận “đã chốt nguyên trạng” như một ngoại lệ baseline mặc định.** Có thể freeze snapshot để tái lập nghiên cứu, nhưng việc promote cần gate riêng. Không ghi đè hoặc xóa snapshot lỗi.

## 3. Trả lời đủ 37 quyết định A–H

Tất cả nội dung dưới đây là đề xuất chốt của gói này. “Review kỹ thuật” nghĩa là người có chuyên môn phải cung cấp bằng chứng trước khi Ngọc phê duyệt hiệu lực.

### A. Product/Governance

| ID | Quyết định đề xuất | Owner/reviewer | Output Tân được nhận hoặc phải tạo |
|---|---|---|---|
| A1 | R1 phục vụ nhà đầu tư cá nhân có danh mục cổ phiếu hiện hữu thuộc universe hỗ trợ; analyst là người dùng phụ. Không robo-advisor đặt lệnh, không AML/KYC. | Ngọc | Persona trong mục 1; giới hạn hiển thị trên UI. |
| A2 | Horizon R1 cố định 20 **phiên giao dịch**. Không cho UI tùy chọn horizon khi chưa validate mô hình tương ứng. S=2000 development; S=5000 target evidence. Cho 2000 ở final chỉ khi sensitivity/CI được review trước evaluation cuối. | Ngọc; Tú/Phúc review | Profile draft; snapshot `horizon_sessions`, `scenario_count` trong mọi run. |
| A3 | Input trực tiếp risk appetite và policy bounds, questionnaire chỉ hỗ trợ giải thích; không tự suy mức chịu lỗ từ câu hỏi chưa validate. Default UI `balanced` phải được người dùng xác nhận. | Ngọc + Phúc | `configs/policies/risk_appetite.yaml`; chưa có risk budget final mặc định. |
| A4 | Claim đúng mức evidence; bắt buộc ghi data date, scenario status, solver thực trả nghiệm, fallback và approval. Không nói đảm bảo lợi nhuận, giảm lỗ thực tế X% từ một cube, tuân thủ toàn bộ pháp luật hay quantum advantage chưa chứng minh. | Ngọc | `configs/policies/claim_policy.yaml`. |
| A5 | Mỗi quyết định có ID, version, proposer/owner, evidence, reviewer, approver, effective date và phạm vi. Gói nháp không kích hoạt runtime. | Ngọc; Tân tích hợp | `decision_registry.yaml`; PR migrate sau phê duyệt. |

### B. Năm change request

| ID | Quyết định đề xuất | Điều kiện hiệu lực và bằng chứng | Owner/reviewer |
|---|---|---|---|
| CR-WF2-001 | Đổi eligibility thành các trạng thái rõ; 252 phiên cho baseline, 126 chỉ research; overall 95%, recent 18/20 research và 20/20 baseline; tối đa 2 phiên thiếu liên tiếp. | Theo lịch sàn/as-of; tách model eligibility với trade eligibility; không xóa holding khỏi risk. Giữ 1 tỷ turnover làm prefilter thử nghiệm, dùng capacity theo NAV/lệnh làm kiểm tra chính. Không cố loại đúng 5–10% mã. | Minh Anh -> Phúc -> Ngọc |
| CR-WF2-002 | Bỏ yêu cầu tăng cash đúng 10%; dùng cash band + risk budget được người dùng/policy xác nhận. Có no-action và infeasible. | Bands draft ở config chỉ calibration. Phúc/Tú cung cấp frontier CVaR/cost/return sacrifice/feasibility theo regime; không tối thiểu hóa CVaR bằng cách mặc định bán tối đa. | Phúc + Tú -> Ngọc |
| CR-WF2-003 | Cash là instrument có yield, cách tính lãi, lag, source/as-of. Cho zero-yield làm sensitivity hoặc đúng loại tài khoản không trả lãi đã xác minh. | Thiếu nguồn: báo `ASSUMPTION_ONLY`, không gắn baseline. Phân biệt cash, proceeds chưa settle và available cash; không giả định dùng tiền bán ngay để sinh lãi. | Phúc -> Ngọc |
| CR-WF2-004 | Universe live dùng snapshot có hiệu lực tại ngày quyết định; historical test dùng membership PIT. | Rổ hiện tại backcast chỉ được gọi retrospective fixed basket. Không thay mã vào quá khứ để làm đẹp history. | Minh Anh -> Ngọc |
| CR-WF2-005 | Dynamic Top-N: thử 10 -> 12 -> 15, chọn N nhỏ nhất qua **cả coverage và stability**; hết danh sách vẫn fail thì dừng baseline. | Không hạ 70% chỉ để pass run này. N tài chính độc lập budget Quantum. >10 ứng viên: ưu tiên classical direct; QAOA subset/decomposition là nghiên cứu riêng có disclosure. | Phúc -> Ngọc; Tân feasibility review |

### C. AI

| ID | Quyết định đề xuất | Việc cần làm / tiêu chí | Owner |
|---|---|---|---|
| C1 | Chưa thay `market_log_return` ngay. Cho benchmark challenger `mean_return_20d`. | Đổi contract version đồng bộ writer/reader nếu challenger được chọn bằng validation; không chọn bằng final holdout. | Tú; Tân contracts |
| C2 | Không dùng một ngưỡng AIC/BIC tuyệt đối chung. Occupancy 5% là diagnostic draft, không đủ để tự PASS. | So sánh cùng dữ liệu/model family; giữ 3-state champion đã đăng ký; báo convergence, state sample, stress event coverage và 10 seed cả thất bại. Ngưỡng final do Tú đề xuất. | Tú + Ngọc |
| C3 | Downside-vol/vol-asymmetry là challenger, không cộng feature vô hạn. | Ablation từng thay đổi; giữ version feature list/scaler; chọn trên development/validation. | Tú |
| C4 | Không bịa lịch sử mã chưa niêm yết cho crash 2018. | Historical replay chỉ trên mã tồn tại lúc đó; proxy/factor scenario là lớp giả định riêng, cần Phúc/Tú validate, ghi uncertainty và không gọi là observed data. | Tú + Phúc |
| C5 | Mở lại quyết định khóa complete-panel 30 mã để đủ stress capability. Không bỏ SSB/VPL khỏi registry chỉ để kéo dài train. | Tách market-feature universe, held portfolio, modelable assets và candidates. Market features dùng index/PIT policy; assets thiếu data giữ residual risk hoặc block. Không renormalize mất mã đang giữ. | Tú + Minh Anh + Phúc |

### D. Risk

| ID | Quyết định đề xuất | Việc cần làm / tiêu chí | Owner |
|---|---|---|---|
| D1 | Mapping posterior -> cash band bằng convex mixture của bands regime là **ứng viên calibration**, không policy final. | Dùng filtered posterior tại t; thêm thử nghiệm độ nhạy/hysteresis nếu giảm churn. User bounds giao với band; giao rỗng trả infeasible. Risk budget user/policy tách với expected return. | Phúc + Tú -> Ngọc |
| D2 | R1 chỉ cash instrument đơn giản, nguồn lãi và lag rõ; không ngầm dùng MMF/term deposit. | Phúc hoàn thiện cash accounting, day-count và phí. Zero là case nghiên cứu nếu chưa xác minh. | Phúc -> Ngọc |
| D3 | Cost engine tách commission, sell tax nếu áp dụng, half-spread, market impact. Không gắn một mức thành quy định chung. | Rate phải theo loại nhà đầu tư/tài khoản/ngày hiệu lực/nguồn. Không double-count spread với liquidity penalty. Phân tích base + conservative cost. | Phúc -> Ngọc |
| D4 | Primary CVaR95; 97,5/99 là robustness. Dùng empirical ES với fractional tail mass khi cần; định nghĩa quantile, dấu loss và weight rõ. | Phúc ghi specification và unit tests ties, S nhỏ, weighted scenarios. Không lấy 20 phiên realized duy nhất để kết luận realized CVaR95/99 đáng tin. | Phúc |
| D5 | Khi risk đã trong budget/band: no-action mặc định nếu lợi ích không material. Khi vượt budget: giảm violation nhưng không vi phạm hard constraints. | Đề xuất objective lexicographic: trong nghiệm đạt budget, ít return sacrifice/cost/turnover; CVaR tie-break. So với CVaR-first như challenger. Weights/scales của QUBO phải fit trên validation và không thay true-objective. | Phúc -> Ngọc |
| D6 | Không chọn cứng Top-15. Chốt quy tắc dynamic N như CR-005. | Đo lại trên data/scenario đã sửa. 59,9/67,5/78,3% chỉ là số cũ. Stability cùng ngày qua seeds/block lengths phải có; qua ngày khác là churn diagnostic, không bắt market chuyển regime vẫn giữ nguyên top. | Phúc + Tú -> Ngọc |
| D7 | Giảm tối đa 30% **vị thế đang nắm giữ** mỗi mã, thêm user cap/liquidity cap/do-not-sell. K = số mã đổi thật, không phải N hay số qubit. | Quy tắc cap, rounding và min trade trong input contract. Không tự nâng cap lên 30% nếu user đặt thấp hơn. | Phúc + Tân -> Ngọc |
| D8 | Giữ oversampling, nhưng sample count scale theo số hệ số; holdout metrics bắt buộc. | `p(q)=1+q+q(q-1)/2`. Train gồm structured + random, val/holdout tách bằng action hashes. Encoding chọn bằng validation; holdout chỉ xác nhận. | Phúc + Tân |
| D9 | Giữ 1 tỷ làm prefilter research trong lúc calibration; không đổi sang 6,6/14,4 tỷ chỉ để đạt tỷ lệ loại mẫu mong muốn. | Capacity thử nghiệm 10% ADV20, sensitivity 5/10/15%, đầy đủ 20 phiên baseline; Phúc kiểm tra với NAV/lệnh. Đây là policy thử nghiệm, không chuẩn pháp lý. | Minh Anh + Phúc -> Ngọc |

### E. Quantum

| ID | Quyết định đề xuất | Việc cần làm / tiêu chí | Owner |
|---|---|---|---|
| E1 | Adaptive cap theo input Risk. Giữ grid 0/10/20/30% làm fixed-grid reference, không âm thầm clip. | Grid adaptive `{0,qmax/3,2qmax/3,qmax}` là challenger khác; lưu action map sau rounding, deduplicate; so sánh cùng effective actions giữa solvers. | Phúc + Tân |
| E2 | Binary là reference; Gray là challenger, chưa duyệt Gray làm mặc định. | Chọn bằng validation, sau đó fresh holdout. Lưu bit order/endian/candidate hash. | Tân + Phúc |
| E3 | Benchmark có hard wall-time/memory/worker budget và ghi toàn bộ retries/failures. | Draft: 600s/seed, 7200s/batch, 1 worker; interactive Quantum async tối đa 300s. Giá trị cần dry-run, không cam kết SLA. Tràn budget dừng process tree thuộc job; fallback classical có deadline riêng. | Tân -> Ngọc |
| E4 | Đánh giá **incremental value** trước khi bàn advantage. Không yêu cầu kết quả phải thắng mới được báo. | So ablation classical-only vs classical+QAOA với ngân sách bằng nhau, cả hai cùng rerank/polish. Không inject exact answer vào QAOA rồi gọi tự tìm. Protocol file 02. | Tân + Phúc -> Ngọc |
| E5 | Futures là P2 research riêng, không blocker release stock+cash hiện tại. | Chỉ mở khi policy hedging/margin và data gate phù hợp được duyệt; chưa dùng dữ liệu settlement để tuyên bố executable hedge đầy đủ. Không thêm qubit futures trong R1. | Ngọc; Phúc/Data review |

### F. Backend/Portfolio

| ID | Quyết định đề xuất | Output / acceptance | Owner |
|---|---|---|---|
| F1 | Nhập quantity + cash + NAV + as-of + restrictions; server reprice. R1 chưa nhận weights-only để tránh hai nguồn chân lý. | Schema đính kèm; client không truyền giá để ghi đè market data. Nhận holdings ngoài model universe để báo lỗi/risk gap, không drop im lặng. | Tân + Phúc; Ngọc UX |
| F2 | Tolerance nháp: `max(10.000 VND, 0,1% declared NAV)`. Đây là engineering UAT threshold chờ Phúc. | Luôn công bố delta. Vượt ngưỡng yêu cầu user xác nhận valuation mới; không tự sửa NAV. `nav_computed` làm mẫu số sau khi reconcile. | Phúc + Tân |
| F3 | Quantity nguyên không âm; không ép holdings vốn có thành round-lot. | Lệnh đề xuất round down theo quy tắc lot đã có source tại t; residual giữ lại và tính risk. R1 chưa hỗ trợ odd-lot order thì báo `BELOW_MIN_TRADE`, không tự bán hết lô lẻ. | Tân + Phúc |

### G. Walk-forward/UAT

| ID | Quyết định đề xuất | Output / acceptance | Owner |
|---|---|---|---|
| G1 | Đăng ký tập ngày bằng quy tắc calendar trước run; không chọn ngày kết quả đẹp. | Khóa cả khoảng train/validation/test, execution lag/cost, data cutoff, seeds, skip reasons. Các giai đoạn đã phân tích chỉ là retrospective; cần holdout mới hoặc forward shadow cho xác nhận độc lập. | Tú + Phúc + Tân |
| G2 | Dùng 16 ca kỹ thuật synthetic để implement trước, sau đó portfolio thật có consent cho UAT. | Không gắn label REAL cho fixtures. Không cần 10 nhà đầu tư khác nhau, nhưng phải đủ ít nhất 10 hành vi UAT và có real-portfolio E2E được Ngọc xác nhận. | Ngọc chuẩn bị; Tân chạy; Phúc review |
| G3 | Chưa ký final PASS. | Evidence ledger đủ 15 DoD PDF §9; phân biệt unit tests/UAT/financial validity. Ngọc ký final trên run/config hash cụ thể, không ký một nhánh code chung chung. | Ngọc |

### H. Config/Artifact

| ID | Quyết định đề xuất | Output / acceptance | Owner |
|---|---|---|---|
| H1 | Tạo profile experimental riêng; giữ snapshot cũ để tái lập; không đổi workflow_update thành baseline mới ngay. | Draft trong gói; Tân viết adapter, migration test và PR sau review. Artifact theo run_id, không trộn `artifacts/dev` nhiều lần chạy. | Tân |
| H2 | Mọi policy có status/owner/version/approved_by/approved_at và effective scope. | Thiếu approval hoặc upstream gate -> không cho baseline. `approved_by=null` là chưa duyệt, không suy ra từ tên tác giả file. | Tân + Ngọc |

## 4. Quyết định Top-N cần hiểu chính xác

1. 30 mã là universe danh mục/thị trường, không phải 30 qubit.
2. Tính risk trên **toàn bộ holdings**, kể cả mã không được trade. Candidate N chỉ giới hạn nơi được thay đổi hành động.
3. Chọn N nhỏ nhất đạt coverage và stability trong 10/12/15. Nếu chỉ có 6 mã held-eligible thì xét toàn bộ 6, không bịa thêm cho đủ 10.
4. Coverage là tỷ trọng tổng **marginal benefit proxy dương** được giữ trong candidates, không đồng nhất % toàn bộ portfolio CVaR được giải thích hay bảo đảm % CVaR sẽ giảm. Luôn báo thêm residual/untradeable risk. Khi action 20% không hợp lệ do cap, phải đăng ký cách tính score trên action feasible thực; không lấy lợi ích từ lệnh không được phép để inflate coverage. Denominator bằng 0 trả diagnostic riêng, không gán coverage=100% tùy ý.
5. N=15 tương ứng 30 decision bits với 4 levels. Slack/ancilla có thể làm số qubit thực lớn hơn. Không mặc định chạy statevector 30-bit trên laptop.
6. Tách hai comparison: cùng N/action-set để so solver; full-N financial solution vs quantum-subset để đánh giá kiến trúc. Không gộp thành bằng chứng solver ưu việt.
7. Nếu dynamic gate không qua, full-eligible classical diagnostic là hướng nghiên cứu đối chiếu; không được lách gate rồi gắn approved recommendation.

## 5. Data/Scenario: mở lại đúng chỗ, không làm lại vô hạn

- Bảo toàn raw và snapshot 14/08. Data Owner phân loại vi phạm thành confirmed vendor issue, confirmed transform issue, corporate action, market/reference rule hoặc unresolved; kèm chứng cứ từng dòng.
- “Giá điều chỉnh đã verified” không nhất thiết phải tự dựng toàn bộ corporate actions nếu vendor có methodology/source evidence đủ tốt; nhưng mã có anomaly material thì không thể dùng chỉ một lời cam kết chung để bỏ qua.
- Không lấy `adjusted_price * raw_volume` làm ADV. Dùng giá/khối lượng thô đồng nhất đơn vị tại phiên; tách adjustment/return khỏi execution data.
- Không dùng `.dropna(how='any')` trên mọi mã để làm HMM chỉ còn lịch sử của IPO mới nhất mà không có quyết định rõ. Tú thiết kế market-feature panel independent với as-of membership/coverage.
- Không fabricate pre-IPO returns. Một holding thiếu mô hình đáng tin phải có proxy được duyệt + uncertainty hoặc block recommendation, không biến mất khỏi NAV/risk.
- Pool Stress = 0 phải báo thiếu, không thay bằng Normal rồi giữ nhãn Stress. Ghi rõ phương pháp moving-block bootstrap, block length, số block độc nhất và reference window.
- Historical crisis replay là baseline/challenge set riêng; bootstrap sinh nhiều mẫu từ cùng pool không làm tăng số sự kiện lịch sử độc lập.
- HMM posterior dùng cho policy phải là thông tin tại t. Nhãn smoothed/Viterbi trên toàn chuỗi chỉ để phân tích hậu nghiệm; không dùng để xây quyết định giả lập tại quá khứ.

## 6. Người cần trả lời và phần Ngọc không cần tự làm

| Người | Cần trả lại | Ngọc quyết định dựa vào |
|---|---|---|
| Minh Anh | Data disposition + sources/effective dates, PIT membership, state/capacity từng holding, data manifest | Phạm vi được hỗ trợ và có thể dùng làm baseline hay chưa |
| Tú | Fit ranges, filtered posterior evidence, stress pool, uncertainty/stability qua seeds, feature ablation | Scenario/HMM có đủ cho mục tiêu giảm tail-risk không |
| Phúc | Budget-band feasibility, cost/yield evidence, candidate stability, true objective, surrogate/financial benchmark | Policy có hợp lý, no-action/infeasible đúng và có giá trị sau cost không |
| Tân | Commit/lockfile/run bundle, API/UI input, QAOA reproducer, bounded jobs, benchmark/raw attempts và artifact reconciliation | Hệ thống có tái lập, trung thực và sử dụng được không |
| Ngọc | Persona/horizon/scope, consent cho UAT, final policy/claim/sign-off | Không thay chữ ký kỹ thuật của các owner bằng cảm nhận về demo |

## 7. Chưa có trong gói này

Chưa có source code của run 14–15/08 đã được đồng bộ; chưa chạy benchmark mới; chưa có investor portfolio thật; chưa có calibrated risk budget/cost/yield final. Không biến các giá trị null thành số tùy ý để chạy PASS. Thiếu các bằng chứng đó không chặn soạn schema, UX, test harness hay chạy nghiên cứu có nhãn rõ.

Các nguồn phương pháp bổ trợ và công thức cụ thể nằm trong file 02. Ngưỡng nội bộ trong gói đều là **đề xuất thử nghiệm**, không tuyên bố là chuẩn pháp lý/chứng nhận tài chính.
