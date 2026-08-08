# configs/

Chỉ còn **2 file YAML** (+ README):

| File | Vai trò |
|---|---|
| `base.yaml` | Tham số mặc định (universe, data, regime, scenarios, risk, quantum) |
| `workflow_update.yaml` | Profile chính — 30→top10→20-bit theo `docs/workflow-v2.md` |

```bash
uv run python -c "from pathlib import Path; from qshield_contracts.config import Config; \
  c=Config.load_profiled(Path('configs/base.yaml'), Path('configs/workflow_update.yaml')); \
  print(c.workflow_runtime())"
```

SoT sản phẩm: `docs/workflow-v2.md`. Status hiện tại: `NON_BASELINE_RUN` đến khi 3 gate ký.
