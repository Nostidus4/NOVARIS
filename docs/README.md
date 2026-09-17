# docs/

Quy ước tên: `YYYY-MM-DD-ten-ngan.md` (chữ thường, không dấu, gạch nối) — ngày là ngày soạn.
Setup và lệnh chạy: `README.md` gốc. Quy tắc kỹ thuật: `CLAUDE.md`.

## Nền tảng (đọc trước)

| File | Dùng để |
|---|---|
| [`workflow-v2.md`](workflow-v2.md) | SoT sản phẩm: kế hoạch, policy, gate, giới hạn (§24) |
| [`disclaimer.md`](disclaimer.md) | Disclaimer bắt buộc cho UI và báo cáo |
| [`folders/`](folders/README.md) | Context từng thư mục code — đọc trước khi sửa code ở đó |

## `decisions/` — quyết định và câu hỏi chờ duyệt

| File | Nội dung | Trạng thái |
|---|---|---|
| [`2026-08-31-phan-hoi-bao-cao-15-08.md`](decisions/2026-08-31-phan-hoi-bao-cao-15-08.md) | Quyết định đề xuất, phản hồi báo cáo 15/08 | Draft chờ Ngọc |
| [`2026-09-04-cau-hoi-cho-ngoc-phuc.md`](decisions/2026-09-04-cau-hoi-cho-ngoc-phuc.md) | Câu hỏi cần Ngọc và Phúc quyết định | Chờ trả lời |

## `reviews/` — rà soát kỹ thuật

| File | Nội dung |
|---|---|
| [`2026-09-04-technical-review.md`](reviews/2026-09-04-technical-review.md) | Review toàn repo + phụ lục đo đạc (đọc Phụ lục J trước). `artifacts_bench/`, `artifacts/runs/job_*` được nhắc tới đã xoá 2026-09-17 — xem git history |

## `data/` — nguồn dữ liệu và sự cố dữ liệu

| File | Nội dung | Trạng thái |
|---|---|---|
| [`2026-09-13-scenario-gate-volatile-loi-tcb.md`](data/2026-09-13-scenario-gate-volatile-loi-tcb.md) | Scenario gate Volatile fail do TCB 2024-06-11 (dữ liệu Yahoo) | Đã đóng |
| [`2026-09-17-chuyen-nguon-gia-fiinpro.md`](data/2026-09-17-chuyen-nguon-gia-fiinpro.md) | Mạnh chuyển nguồn giá sang FiinPro — lưu ý khi dùng dữ liệu | **Hiện hành** |

## `hybrid/` — thí nghiệm QAOA-assisted candidate generation

| File | Nội dung |
|---|---|
| [`2026-09-13-phuong-an-quantum-assisted.md`](hybrid/2026-09-13-phuong-an-quantum-assisted.md) | Phương án gốc (nguồn của plan) |
| [`2026-09-13-plan-qaoa-assisted.md`](hybrid/2026-09-13-plan-qaoa-assisted.md) | Plan chính thức, track, gate H1–H6 |
| [`2026-09-13-provenance-exploratory.md`](hybrid/2026-09-13-provenance-exploratory.md) | Pha 0: truy nguồn số exploratory cũ |
| [`2026-09-13-de-xuat-coupled-constraints.md`](hybrid/2026-09-13-de-xuat-coupled-constraints.md) | Đề xuất instance ràng buộc ghép — chưa chạy |

Config thí nghiệm: `configs/experiments/hybrid_v*.yaml`. Kết quả: `artifacts/runs/hybrid_qaoa_assisted_v*/`.
