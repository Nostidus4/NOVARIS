# data/ · artifacts/ · reports/

Thư mục I/O và exploration — **không** chứa core logic sản phẩm.

## `data/`

- Raw / processed market data (thường gitignore).
- Pipeline đọc/ghi qua `ArtifactPaths` + config path, không hard-code.
- Metadata nguồn nên khớp Source Registry (workflow-v2 §7).

## `artifacts/`

- Output pipeline: `dev/` (lặp nhanh) hoặc `runs/<run_id>/` (có version).
- Layout đích V2: workflow-v2 §18.
- Mỗi số trên slide/demo phải truy về một `run_id` + config hash.
- Chỉ báo cáo run gắn `profile_id=workflow_update`; không trộn số liệu run khác scope.


## `reports/`

- Báo cáo người đọc (PDF/MD/HTML) sinh từ artifact — không phải nguồn tính toán.


## Context cho Claude

- Chỉ `RunContext` ghi metadata chuẩn (`config.json`, `metrics.json`, `logs.txt`…).
- Module tính toán trả data; orchestration (pipeline/backend job) quyết định ghi đâu.
- Khi debug: ưu tiên đọc artifact + `logs.txt` của đúng `run_id`, đừng sửa tay số trong JSON để “cho đẹp”.
