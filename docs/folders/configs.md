# configs/

**Owner duyệt:** Nguyễn Thị Ánh Ngọc
**Cấu trúc — 2 file YAML:**

| File | Vai trò |
|---|---|
| `configs/base.yaml` | Mặc định: universe 30 mã, data, HMM, scenarios, cost, QAOA seeds |
| `configs/workflow_update.yaml` | Profile SoT vận hành 20-bit (+ số Decision-package đã gộp) |

```python
from pathlib import Path
from qshield_contracts.config import Config

cfg = Config.load_profiled(
    Path("configs/base.yaml"),
    Path("configs/workflow_update.yaml"),
)
```

Chi tiết policy: [`../workflow-v2.md`](../workflow-v2.md).
