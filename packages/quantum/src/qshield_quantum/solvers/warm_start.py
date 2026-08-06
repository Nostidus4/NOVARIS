# Đỗ Ngọc Tân - tùy chọn — khởi tạo warm-start cho QAOA.
"""ĐỂ TRỐNG có chủ đích ở vòng đầu (`plan.md` câu hỏi 2).

`configs/quantum.yaml` có dòng comment trích từ thiết kế PSS gốc ("Warm-start QAOA p=1 là cấu hình
chính") nhưng đó là spec cho bài toán 20-bit/10-candidate — `docs/Structure.md` liệt kê file này là
*"tùy chọn"* cho phạm vi đã khóa. Với 8 qubit, `solvers/qaoa.py` (QAOA p=1 thường, không warm-start)
đã hội tụ đủ tốt trong benchmark ban đầu — chưa có lý do thêm độ phức tạp của warm-start (relaxation
liên tục + mixer tùy biến). Viết file này SAU nếu benchmark cho thấy QAOA thường không đủ tốt.
"""
