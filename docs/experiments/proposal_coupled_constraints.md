# Đề xuất cho Phúc/Ngọc duyệt — instance có ràng buộc ghép (protocol v4, CHƯA CHẠY)

Trạng thái: `DRAFT_PENDING_RISK_PRODUCT_APPROVAL` · Ngày: 2026-09-13

## Vì sao cần

Exploratory v1–v3 cho thấy surrogate workflow gần như **tách rời theo từng mã**:
|Q| ≈ 2e-5 so với |linear| ≈ 0,04 (tỷ lệ ~2000×), Spearman(energy, true objective) ≈ 1,0, và ở 4/5
instance nghiệm tối ưu là "bán 30% mọi candidate". Bài toán tách rời được classical giải bằng cách
xét từng mã độc lập, nên **không bộ sinh ứng viên nào — kể cả QAOA — có thể tạo giá trị tăng thêm**
trên các instance này. Đây là đặc tính của objective/policy hiện tại, không phải của solver.

## Nguyên tắc (không được vi phạm)

- Ràng buộc phải là **yêu cầu sản phẩm có thật**, được Risk owner (Phúc) và Product owner (Ngọc)
  chấp thuận *trước*; không chọn vì nó giúp QAOA.
- Không đổi trọng số objective để classical khó hơn.
- Experiment_id mới, manifest khóa mới, confirmation mới. Kết quả v3 giữ nguyên.

## Các ràng buộc ứng viên (cần owner chọn và đặt ngưỡng)

| Ràng buộc | Ý nghĩa sản phẩm | Vì sao tạo tương tác giữa các mã |
|---|---|---|
| Số lệnh tối đa `K` (cardinality) | Nhà đầu tư cá nhân không muốn đặt 8 lệnh; phí cố định/lệnh | Chọn mã này loại mã khác ⇒ bài toán tổ hợp, không tách rời |
| Trần turnover tổng | Giới hạn thanh khoản/thuế giao dịch | Tổng % bán bị chia sẻ giữa các mã |
| Dải tiền mặt sau hedge `[c_min, c_max]` hai phía | Không bán quá mức cần | Ràng buộc tổng có trọng số theo tỷ trọng |
| Giới hạn theo ngành | Không xả toàn bộ nhóm ngân hàng | Ghép các mã cùng ngành |
| Quy mô lệnh tối thiểu | Lệnh quá nhỏ không đáng khớp | Mức 10% bị loại với mã tỷ trọng thấp |

## Hiện thực kỹ thuật đã có sẵn

- Predicate QUBO đã hỗ trợ `min/max_active_candidates`, `min/max_total_action_pct`
  (`workflow.make_four_level_feasibility`, `generators.common.constraint_mask`).
- `RiskPolicy` đã chấm do_not_sell, per-asset cap, cash band, turnover, CVaR budget ở true objective.
- Cần thêm khi được duyệt: (a) cardinality vào `RiskPolicy`/`evaluate_policy_constraints`;
  (b) QAOA với ràng buộc cardinality — hoặc penalty trong QUBO (phải qua `verify/consistency.py`),
  hoặc XY-mixer bảo toàn Hamming weight (chỉ tìm trong miền hợp lệ); (c) random baseline lấy mẫu
  đúng miền hợp lệ (đã có trong `random_pool` qua predicate).

## Câu hỏi cần owner trả lời

1. Ràng buộc nào trong bảng là yêu cầu sản phẩm R1? Ngưỡng (K, turnover cap, dải tiền mặt)?
2. Có áp cho mọi archetype hay chỉ archetype cụ thể?
3. Materiality cho claim: giữ `materiality_normalized_min = 0.01` hay đổi?
