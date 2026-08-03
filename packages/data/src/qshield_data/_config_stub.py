"""Đọc tạm `configs/*.yaml`, thay cho `qshield_contracts.config.Config`.

`packages/contracts/src/qshield_contracts/config.py` hiện vẫn là scaffold (chưa có thân hàm — xem
`docs/Structure.md` §3, đây là nơi *duy nhất* lẽ ra được mở file yaml). Trong lúc chờ, module này
là chỗ duy nhất trong `qshield_data` được phép gọi `open()`/`yaml.safe_load` trên `configs/*.yaml`.

CHỈ được import từ `qshield_data.cli` — mọi hàm logic khác trong package (`sources/`, `clean/`,
`returns.py`, `features.py`, `eligibility.py`, `split.py`, `quality/`, `manifest.py`, `loader.py`)
PHẢI nhận dữ liệu qua tham số tường minh, không tự đọc yaml (ràng buộc trong `plan.md`).

TODO: xóa file này, thay bằng `qshield_contracts.config.Config` ngay khi package đó được implement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(base_yaml: Path) -> dict[str, Any]:
    """Đọc `base_yaml` và gộp các file trong khóa `includes:` (cùng thư mục với `base_yaml`).

    Key top-level của từng file include được gộp vào một dict phẳng duy nhất; nếu hai file include
    trùng key, file đứng sau trong danh sách `includes` đè lên file đứng trước. Key của chính
    `base_yaml` (`seed`, `artifacts`, `logging`, `data`, `paths`, ...) đè lên tất cả include.
    """
    base_yaml = Path(base_yaml)
    config = _load_yaml(base_yaml)
    includes = config.pop("includes", []) or []
    merged: dict[str, Any] = {}
    for name in includes:
        merged.update(_load_yaml(base_yaml.parent / name))
    merged.update(config)
    return merged
