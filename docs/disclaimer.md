# Disclaimer — Tuyên bố miễn trừ trách nhiệm

Văn bản **bắt buộc**. Phải xuất hiện tại:

- Khu vực kết quả cuối cùng của dashboard (Final Recommendation / Before–After panel).
- Mọi báo cáo, bản export và pitch deck có kèm số liệu từ Q-SHIELD.
- Demo khi trình bày trước giám khảo.

Không được rút gọn nội dung theo hướng làm giảm mức độ rõ ràng của cảnh báo.

Kế hoạch / claim rules: [`workflow-v2.md`](workflow-v2.md) §24.

---

## Nội dung disclaimer

> Q-SHIELD là hệ thống hỗ trợ phân tích và ra quyết định quản trị rủi ro dựa trên dữ liệu lịch sử,
> mô hình thống kê, mô phỏng và tối ưu. Hệ thống **không tự động đặt lệnh**, **không thay thế tư vấn
> đầu tư được cấp phép**, **không bảo đảm lợi nhuận** và **không bảo đảm ngăn ngừa tổn thất** trong
> mọi điều kiện thị trường. Kết quả phụ thuộc vào dữ liệu, giả định chi phí, mô hình sinh kịch bản,
> QUBO surrogate và cấu hình solver.

Bản mở rộng (báo cáo kỹ thuật / pitch, không rút gọn):

> Q-SHIELD là một **prototype dự thi**, không phải sản phẩm tư vấn đầu tư đã qua thẩm định pháp lý.
> Hệ thống mô tả kịch bản rủi ro và đề xuất phương án chuyển một phần vị thế sang tiền mặt; hệ thống
> không gửi lệnh đến công ty chứng khoán và không tự động thực hiện bất kỳ giao dịch nào. Việc sử
> dụng danh sách cổ phiếu cố định tại một ngày snapshot để hồi cứu qua nhiều năm có thể tạo
> survivorship bias — kết quả phải được hiểu là nghiên cứu trên *fixed current-constituent
> universe*, không phải backtest trên thành phần lịch sử theo từng thời điểm. Kết quả QAOA luôn
> được trình bày cùng benchmark exact/classical trên cùng một QUBO; hệ thống **không tuyên bố quantum
> advantage** khi chưa có bằng chứng phù hợp về tài nguyên và chất lượng nghiệm. Mọi kết luận trình
> bày phải nằm trong phạm vi bằng chứng mà artifact của run tương ứng hỗ trợ.

---

## Không được tuyên bố

- Quantum advantage khi chưa chứng minh theo tiêu chuẩn đã đăng ký.
- QAOA luôn tốt hơn exact/classical.
- Quantum tạo lợi nhuận hoặc loại bỏ hoàn toàn tail risk.
- Kết quả là khuyến nghị mua/bán chắc chắn sinh lời.
- Dự báo giá hoặc tín hiệu trading ngắn hạn.
- Correlation / model output như quan hệ nhân quả.

## Được phép tuyên bố

- Đã biểu diễn bài toán coarse hedging dưới dạng QUBO.
- Đã chạy QAOA và so sánh trên cùng QUBO với exact/classical.
- Quantum tham gia chọn tài sản và mức giảm vị thế.
- Kết quả tái lập được qua `run_id`, config, seed và artifact.
