# packages/pipeline/

**Owner:** Đỗ Ngọc Tân
**Vai trò:** Orchestrator end-to-end — gọi từng stage theo thứ tự, gắn `run_id`, không chứa công thức.

## Nhiệm vụ

- CLI `qshield-pipeline` chạy `all` hoặc từng stage.
- Điều phối data → regime → scenarios → risk → quantum → rerank/benchmark theo profile.
- Tạo `RunContext`, ghi metadata run.
- Tôn trọng `configs/workflow_update.yaml` → `pipeline.stages`.

## Cây chính

```text
qshield_pipeline/
  cli.py
  run.py
  stages.py
```

## Được làm

- Gọi public API / CLI của `data`, `ai`, `risk`, `quantum`.
- Truyền config + paths tường minh.
- Fail fast khi stage trước FAIL gate (theo profile).

## Không được làm

- Tự tính CVaR / QUBO trong pipeline.
- Hard-code path artifact.
- Bỏ qua gate / chạy ngoài scope `workflow_update` rồi báo như baseline.
- Ghi `config.json` / `metrics.json` ngoài `RunContext`.

## Context cho Claude

- Entry:

```bash
uv run qshield-pipeline all --config configs/base.yaml --mock
uv run qshield-pipeline all --config configs/base.yaml
```

- Optimize job từ backend nên spawn pipeline/CLI — không import tắt quantum vào router.
- Stage list / owner: `configs/workflow_update.yaml` khóa `pipeline.stages`.
- Thứ tự P0 trước Quantum: [`../workflow-v2.md`](../workflow-v2.md) §2.3, §21.

## Test

```bash
uv run pytest packages/pipeline -q
```
