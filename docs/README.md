# docs/

Tài liệu sản phẩm / kiến trúc / vận hành. **Đọc `CLAUDE.md` + `docs/limitations.md` trước khi
claim số liệu.**

## Bản đồ nhanh

| Thư mục / file | Dùng khi |
|---|---|
| `product/` | Scope, PRD, AC, RTM, disclaimer — Product Owner |
| `architecture/` | Hợp đồng dữ liệu, pipeline, backend, quyết định AI đã adopt |
| `handoffs/` | Input chờ owner (Decision-package, gate ask, open inputs) |
| `runbook/` | Setup, demo, troubleshooting |
| `perf/` | Báo cáo đo runtime / bug đã verify theo ngày |
| `archive/` | Bản nháp đã supersede — giữ để truy vết, **không** dùng làm nguồn hiện hành |
| `limitations.md` | Giới hạn bằng chứng (bắt buộc đọc trước slide) |
| `benchmark_plan.md` | Checklist benchmark solver |
| `Structure.md` | Bản đồ repo + phân công |

## `perf/` — giữ những file nào

Mọi file trong `perf/` là **bằng chứng đã đo** (được code/test dẫn chiếu). Không xóa vì “cũ ngày”:

- `2026-08-04-pipeline-timing.md` — Typer / run_id / subprocess isolation
- `2026-08-04-scenario-scaling.md` — scale S
- `2026-08-05-kurtosis-fail-vcb.md` — corporate actions / Adj Close
- `2026-08-06-quantum-pipeline-implementation.md` — quantum stage lên pipeline
- `2026-08-06-workflow-update-downstream.md` — đường downstream + timing exact-only
- `2026-08-07-qaoa-solver-benchmark.md` — exact vs classical vs QAOA (báo cáo gửi nhóm)

## `archive/`

- `ai-scope-decision-record-v0.1.md` — superseded bởi `architecture/ai-decisions-v0.2.md`
