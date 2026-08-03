# Đỗ Ngọc Tân - đọc & gộp configs/*.yaml qua includes — nơi DUY NHẤT trong repo được mở file yaml.
"""`Config` — nơi DUY NHẤT trong repo được phép `open()`/`yaml.safe_load` trên `configs/*.yaml`.

Port thẳng từ `qshield_data/_config_stub.py::load_config` (đã chạy thật trên dữ liệu thật, xem
`packages/data/src/qshield_data/cli.py`) — không đổi hành vi merge, chỉ đổi chỗ sống. `_config_stub`
bị xóa sau khi module này thay thế nó (plan-contracts.md §4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class Config(dict):
    """Config đã merge từ `base_yaml` + các file trong khóa `includes:`.

    Kế thừa `dict` (không phải pydantic model) để mọi call site hiện tại (`cfg["date_range"]`,
    `cfg.get("eligibility", {})`) dùng được ngay không cần sửa gì ngoài import — quyết định "nhẹ"
    trong plan-contracts.md §6 câu 1.
    """

    @classmethod
    def load(cls, base_yaml: Path) -> Config:
        """Đọc `base_yaml`, gộp các file trong khóa `includes:` (cùng thư mục với `base_yaml`).

        Key top-level của từng file include được gộp vào một dict phẳng duy nhất; nếu hai file
        include trùng key, file đứng sau trong danh sách `includes` đè lên file đứng trước. Key của
        chính `base_yaml` (`seed`, `artifacts`, `logging`, `data`, `paths`, ...) đè lên tất cả include.
        """
        base_yaml = Path(base_yaml)
        config = _load_yaml(base_yaml)
        includes = config.pop("includes", []) or []
        merged: dict[str, Any] = {}
        for name in includes:
            merged.update(_load_yaml(base_yaml.parent / name))
        merged.update(config)
        return cls(merged)


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
