# Disclaimer — Tuyên bố miễn trừ trách nhiệm

Văn bản này là nội dung **bắt buộc** (nguồn: `docs/product/product_requirements.md` Phụ lục B và
`docs/product/mvp_scope.md` §25). Phải xuất hiện tại:

- Khu vực kết quả cuối cùng của dashboard (Final Recommendation / Before–After panel).
- Mọi báo cáo, bản export và pitch deck có kèm số liệu từ Q-SHIELD.
- Demo script khi trình bày trước giám khảo.

Không được rút gọn nội dung theo hướng làm giảm mức độ rõ ràng của cảnh báo.

---

## Nội dung disclaimer

> Q-SHIELD là hệ thống hỗ trợ phân tích và ra quyết định quản trị rủi ro dựa trên dữ liệu lịch sử,
> mô hình thống kê, mô phỏng và tối ưu. Hệ thống **không tự động đặt lệnh**, **không thay thế tư vấn
> đầu tư được cấp phép**, **không bảo đảm lợi nhuận** và **không bảo đảm ngăn ngừa tổn thất** trong
> mọi điều kiện thị trường. Kết quả phụ thuộc vào dữ liệu, giả định chi phí, mô hình sinh kịch bản,
> QUBO surrogate và cấu hình solver.

Bản mở rộng (dùng cho báo cáo kỹ thuật và pitch, không rút gọn):

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

## Những điều nhóm KHÔNG được tuyên bố

Theo `docs/product/mvp_scope.md` §11.5:

- Có quantum advantage nếu chưa chứng minh theo tiêu chuẩn tài nguyên và chất lượng nghiệm phù hợp.
- QAOA luôn tốt hơn exact/classical solver.
- Quantum tạo lợi nhuận hoặc loại bỏ hoàn toàn tail risk.
- Kết quả là khuyến nghị mua/bán chắc chắn sinh lời.
- Q-SHIELD dự báo giá cổ phiếu hoặc tạo tín hiệu trading ngắn hạn.
- Correlation hoặc model output được mô tả như quan hệ nhân quả.

## Những điều nhóm ĐƯỢC phép tuyên bố

- Đã biểu diễn bài toán coarse hedging dưới dạng QUBO.
- Đã chạy QAOA và so sánh trên cùng QUBO với exact/classical solver.
- Quantum tham gia trực tiếp vào việc chọn tài sản bị tác động và mức giảm vị thế.
- Đã kiểm định ảnh hưởng của surrogate (và polishing, ở phần thiết kế đầy đủ).
- Kết quả có thể tái lập: mỗi con số truy xuất được về `run_id`, config, seed và artifact nguồn.

---

## Vị trí bắt buộc khác

- README.md dòng giới thiệu: *"Prototype dự thi. Không phải khuyến nghị đầu tư."*
- `CLAUDE.md` mục "Bối cảnh": hệ thống mô tả kịch bản rủi ro, không đưa khuyến nghị mua bán.
- Giới hạn kỹ thuật/phương pháp chi tiết: xem `docs/limitations.md`.
