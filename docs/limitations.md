# Giới hạn của Q-SHIELD

Tài liệu này liệt kê những gì Q-SHIELD **không làm được** hoặc **không nên bị hiểu nhầm là làm được**.
Đây là căn cứ bắt buộc phải đọc trước khi trình bày kết quả, và phải được dẫn lại trong mọi báo cáo,
dashboard (khu vực Audit/Limitations) và bản export. Xem thêm `docs/product/disclaimer.md` cho tuyên
bố miễn trừ trách nhiệm dành cho người dùng cuối.

---

## 1. Phạm vi hiện tại đã bị thu hẹp so với thiết kế sản phẩm gốc

`docs/product/mvp_scope.md` và `docs/product/product_requirements.md` mô tả một thiết kế đầy đủ:
universe 30 mã VN30, chọn động top 10 ứng viên, mã hóa 20 bit (2 bit/mã), 4 mức hành động
(0/10/20/30%), 2.000–5.000 kịch bản. Đây là baseline **Baseline Candidate**, còn nhiều mục `TBD`
chưa khóa.

Do ràng buộc 7 ngày / 5 người, `CLAUDE.md` và `docs/Structure.md` khóa một phạm vi kỹ thuật **nhỏ
hơn** để bảo đảm chạy được đầu-cuối:

| Thông số | Thiết kế gốc (PSS/PRS) | Phạm vi đã khóa (CLAUDE.md) |
|---|---|---|
| Universe | 30 mã VN30 | 8 mã |
| Số ứng viên Quantum | Top 10 (động) | Cả 8 mã |
| Số bit QUBO | 20 bit (2 bit/mã) | Tương ứng chọn đúng K=3 hành động trong 8 mã |
| Mức hành động | 0% / 10% / 20% / 30% | Một mức duy nhất: giảm 20% vị thế |
| Số kịch bản | 2.000 (dev) / 5.000 (final) | 500 |
| Horizon | 20 ngày | 20 ngày |
| Local polishing (±5pp) | Có | Không có trong phạm vi đã khóa |

**Khi đọc bất kỳ số liệu nào từ hệ thống, phải hiểu đó là kết quả trên phạm vi đã khóa (8 mã, K=3,
giảm 20%), không phải trên thiết kế 30-mã/top-10/20-bit mô tả trong Product Scope.** Nếu về sau mở
rộng theo đúng thiết kế gốc, đây không phải là điều chỉnh nhỏ mà là Change Request theo
`docs/product/mvp_scope.md` §22.

---

## 2. Giới hạn dữ liệu

- **Survivorship bias:** dùng danh sách mã cố định tại một ngày snapshot để chạy hồi cứu qua nhiều
  năm tạo thiên lệch sống sót. Kết quả phải được trình bày là nghiên cứu trên *fixed
  current-constituent universe*, không phải backtest trên thành phần VN30 lịch sử theo từng thời
  điểm (point-in-time).
- **Không nội suy dữ liệu trước ngày niêm yết.** Mã chưa đủ lịch sử tối thiểu bị loại khỏi
  eligibility tại ngày đánh giá đó, không được gán giá trị giả định.
- **Không forward-fill lợi suất.** Giá thiếu được xử lý theo quy tắc trong `configs/data.yaml` và
  phải ghi log; `.ffill()` trên cột return là bug, không phải giải pháp.
- **Tần suất dữ liệu là ngày (daily).** Không có dữ liệu intraday, tick hay order book — hệ thống
  không phản ánh được biến động trong phiên.
- **Nguồn dữ liệu, quyền sử dụng và độ trễ cập nhật** phụ thuộc vào Source Registry; không có
  real-time streaming hay cảnh báo liên tục.

## 3. Giới hạn mô hình thống kê (HMM + kịch bản)

- Gaussian HMM giả định 3 trạng thái là **giả thuyết kỳ vọng**, không phải sự thật tuyệt đối về thị
  trường; state có thể không hội tụ ổn định qua các seed, và khi đó hệ thống rơi về
  `baseline/rule_based_regime.py` — kết quả từ fallback này yếu hơn HMM và phải được công bố rõ.
- Xác suất trạng thái (bao gồm `p_stress`) là ước lượng thống kê trên dữ liệu lịch sử, **không phải
  dự báo chắc chắn** về tương lai.
- Kịch bản stress được sinh bằng regime-conditioned moving-block bootstrap trên dữ liệu lịch sử —
  nếu tương lai xảy ra một loại cú sốc chưa từng có trong lịch sử (never-seen-before shock), tập
  kịch bản sẽ không phủ được tình huống đó.
- CVAE (nếu được bật) chỉ là challenger; nếu không đạt kiểm định phân phối, hệ thống phải quay lại
  bootstrap — không được tự ý dùng CVAE khi validation không pass.

## 4. Giới hạn của lớp Quantum

- **QUBO là xấp xỉ bậc hai (surrogate)** của hàm mục tiêu tài chính thật, không phải hàm mục tiêu
  gốc. Vì vậy nghiệm QAOA/exact trên QUBO **luôn phải được Risk Engine chấm lại bằng true CVaR**
  trước khi trở thành khuyến nghị cuối — không bao giờ chọn phương án chỉ dựa trên QUBO energy.
- **Không tuyên bố quantum advantage.** Nếu QAOA thua exact solver hoặc thua một baseline cổ điển,
  kết quả phải được báo cáo trung thực đúng như vậy. Đây là yêu cầu nghiệm thu, không phải tùy chọn.
- **Simulator, không phải phần cứng lượng tử thật.** `backends/hardware.py` cố ý để trống; mọi kết
  luận về runtime/hiệu năng chỉ có giá trị trên simulator (`StatevectorSampler`), không suy diễn
  sang phần cứng lượng tử thực.
- **Exact solver là thước đo QUBO-level optimality, không phải bằng chứng tối ưu tài chính.** Nếu
  surrogate khớp kém với hàm mục tiêu thật, nghiệm "exact" trên QUBO vẫn có thể không tối ưu về tài
  chính — đây chính là lý do bắt buộc phải re-rank bằng true objective.
- QAOA chạy trên số seed hữu hạn (baseline ≥ 10); không được cherry-pick seed tốt nhất để báo cáo.

## 5. Giới hạn tài chính và hành động phòng vệ

- Cơ chế phòng vệ **chỉ là cash-only**: giảm một phần vị thế và chuyển sang tiền mặt. Không có
  phái sinh (futures/options/warrants), không short selling, không margin/leverage, không mua tăng
  tỷ trọng.
- Cash-only mitigation **giảm exposure nhưng không loại bỏ hoàn toàn** market risk, liquidity risk,
  gap risk hay model risk.
- Transaction cost, thuế bán và slippage được mô hình hóa bằng proxy có nguồn giả định trong
  `configs/risk.yaml`; đây không phải chi phí thực tế đo được tại thời điểm giao dịch của từng công
  ty chứng khoán.
- CVaR 99% có ít quan sát đuôi hơn, khoảng tin cậy rộng hơn CVaR 95% — không nên dùng CVaR 99% làm
  chỉ tiêu ra quyết định chính, chỉ dùng để kiểm tra độ bền (robustness).

## 6. Giới hạn về vai trò và phạm vi hệ thống

- Q-SHIELD là **hệ thống hỗ trợ quyết định (decision-support)**, không phải hệ thống thực thi giao
  dịch. Hệ thống không tự gửi lệnh, không kết nối công ty chứng khoán/broker.
- Đây là **prototype dự thi**, không phải sản phẩm tư vấn đầu tư đã qua thẩm định pháp lý.
- Không đảm bảo lợi nhuận, không đảm bảo giảm lỗ trong mọi điều kiện thị trường.
- Dashboard chỉ đọc và hiển thị số liệu từ artifact đã tính; nếu dashboard và artifact lệch nhau thì
  artifact là nguồn sự thật, không phải dashboard.

## 7. Danh sách rủi ro sản phẩm đã biết và biện pháp kiểm soát

| Rủi ro | Ảnh hưởng | Kiểm soát |
|---|---|---|
| Survivorship bias từ universe cố định | Kết quả hồi cứu có thể lạc quan hơn thực tế | Công bố limitation; không gọi là backtest lịch sử VN30 |
| Thiếu dữ liệu lịch sử ở một số mã | Giảm coverage, giảm độ tin cậy | Không nội suy trước niêm yết; lọc theo eligibility |
| HMM không hội tụ / không ổn định | Narrative trạng thái và kịch bản kém tin cậy | Multi-seed, AIC/BIC, occupancy check, fallback rule-based |
| Kịch bản không giữ đúng tail/tương quan chéo | CVaR tính ra không đáng tin | Bootstrap theo vector 8 tài sản mỗi ngày (không bootstrap độc lập từng mã), validation battery |
| QUBO surrogate xếp hạng kém so với hàm thật | QAOA energy tốt nhưng CVaR thực không cải thiện | Bắt buộc true-objective re-ranking bằng `qshield_risk.evaluate` |
| QAOA chạy chậm/không ổn định trên simulator | Gián đoạn demo | Cache kết quả, `p=1`, giảm shots/seed ở dev mode, fallback exact |
| Hiểu nhầm là khuyến nghị đầu tư | Rủi ro đạo đức và pháp lý | Disclaimer bắt buộc tại mọi khu vực kết quả, không tự thực thi giao dịch |

---

## 8. Cách trình bày đúng khi có giới hạn

Khi một chỉ tiêu không đạt ngưỡng kỳ vọng (ví dụ CVaR sau hedge không giảm, hoặc QAOA thua classical
baseline), giao diện và báo cáo **phải hiển thị đúng thực tế đó**, không dùng màu sắc hay ngôn ngữ
gây hiểu nhầm là thành công. Không đặt lại ngưỡng đánh giá sau khi đã xem kết quả để làm đẹp báo cáo.

Tham khảo thêm: `CLAUDE.md` (mục "Bối cảnh" và "Đóng băng phạm vi"), `docs/product/mvp_scope.md`
§§15, 17–19, 25, `docs/product/product_requirements.md` Phụ lục B.
