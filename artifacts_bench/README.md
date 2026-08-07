# artifacts_bench/

Solver bakeoff outputs (`NON_BASELINE_RUN`). **Không** trộn với `artifacts/dev/` (pipeline sản phẩm).

| Thư mục | Giữ? | Nội dung |
|---|---|---|
| `warm_start_run/` | yes | 10-bit QAOA + warm-start + true_benchmark |
| `no_warm_start_run/` | yes | 10-bit QAOA không warm-start |
| `stress_run/` | yes | Stress QUBO bakeoff JSON |
| `narrative_run/` | yes | Scaling + depth scan (notebook 06) |
| `dev/` | **no — regenerable** | Copy regime/scenarios tạm khi chạy prepare; đã gitignore, xóa local được |

Tái tạo `dev/` khi cần chạy lại bakeoff 10-bit:

```bash
mkdir -p artifacts_bench/dev
cp -R artifacts/dev/regime artifacts/dev/scenarios artifacts_bench/dev/
uv run qshield-risk prepare-workflow \
  --config configs/base.yaml \
  --profile configs/profiles/workflow_update.yaml \
  --override configs/provisional/qaoa_benchmark_10bit.yaml
```
