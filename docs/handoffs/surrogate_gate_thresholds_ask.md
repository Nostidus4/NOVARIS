# Note hỏi owner — Surrogate Gate thresholds (TL-014)

**Trạng thái:** PROVISIONAL — đã chấp nhận để code validation hook xong trước; **chưa** phải số
chốt cho baseline/UAT.

**Ai cần hỏi:** Liêu Hoài Phúc (Risk) + Đỗ Ngọc Tân (Quantum) đề xuất → Nguyễn Thị Ánh Ngọc duyệt.

**Vì sao cần hỏi:** Decision-package TL-014 yêu cầu Surrogate Gate có MAE/RMSE, Spearman, top-k
recall, feasible rate, seed stability. Nếu fail thì không dùng QUBO/QAOA làm baseline. Nhưng
Decision-package **chưa ghi số ngưỡng cụ thể**, nên code tạm dùng giá trị dưới đây trong
`configs/provisional/workflow_update_downstream.yaml` khóa `surrogate_validation`.

## Giá trị provisional đang dùng

| Metric | Provisional threshold | Ý nghĩa khi hỏi |
|---|---:|---|
| `mae_max` | `0.02` | Sai số tuyệt đối trung bình của surrogate vs true objective (cùng scale objective) |
| `rmse_max` | `0.03` | RMSE cùng đơn vị |
| `spearman_min` | `0.70` | Tương quan hạng tối thiểu giữa surrogate energy và true objective |
| `top_k_recall_min` | `0.60` | Với k=20, tỷ lệ nghiệm true-top-k nằm trong surrogate-top-k |
| `feasible_rate_min` | `0.05` | Tỷ lệ sample QAOA feasible tối thiểu (phụ thuộc constraint) |
| `seed_stability_min` | `0.50` | Overlap bitstring tốt nhất giữa các seed / ổn định xếp hạng (chi tiết implement) |

Config version gắn với các số này: xem `provenance.config_version` trong provisional yaml.

## Câu hỏi gửi nhóm

1. Các ngưỡng trên có chấp nhận làm **dev gate** không? Nếu không, số chính thức là bao nhiêu?
2. Top-k recall dùng `k=10` hay `k=20` (khớp TL-016 rerank top 20)?
3. Spearman / MAE đo trên structured samples (137/211) hay trên tập hold-out riêng? Nếu hold-out:
   bao nhiêu sample random/validation thêm?
4. Khi surrogate fail: **hard stop** solver, hay chỉ gắn exception + `NON_BASELINE_RUN` (Decision
   đang nghiêng hard stop cho baseline)?
5. Ai ký Surrogate Gate trước mỗi final run — Phúc, Tân, hay cả hai?

## Việc làm sau khi có câu trả lời

- [ ] Thay đúng số vào config (không hard-code trong Python).
- [ ] Tăng `config_version`.
- [ ] Gỡ nhãn provisional khỏi Surrogate Gate nếu đã duyệt.
- [ ] Chạy lại fit QUBO + exact + QAOA + true rerank.
- [ ] Cập nhật RTM / test evidence.

**Không** chỉnh ngưỡng sau khi đã nhìn kết quả final để “làm đẹp báo cáo”.
