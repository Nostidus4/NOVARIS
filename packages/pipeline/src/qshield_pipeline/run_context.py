# Đỗ Ngọc Tân - tạo artifacts/runs/run_YYYYMMDD_HHMM/ theo artifacts.mode trong configs/base.yaml.
"""`PipelineRunContext` — sinh MỘT `run_id` dùng chung cho toàn bộ 5 bước (data → regime →
scenarios → risk → optimize), khớp fix cho bug đã đo ở
`docs/perf/2026-08-04-pipeline-timing.md` §6: mỗi CLI con (`qshield_ai`, `qshield_quantum`) tự gọi
`_resolve_run_id()` riêng, nên chạy độc lập nhiều lần sẽ sinh nhiều `run_id` khác nhau cho cùng một
lần chạy pipeline khi `artifacts.mode: runs`.

Không tạo `RunContext` MỚI cho từng bước — mỗi bước vẫn tự ghi `config.json`/`metrics.json` của
CHÍNH nó qua `RunContext` riêng (CLAUDE.md quy tắc 13: module tính toán/CLI của package đó ghi
metadata của chính nó, `pipeline` không ghi thay). Cách pipeline chia sẻ `run_id`: tiêm khóa
`run_id` vào bản config đã merge rồi ghi ra một file tạm, dùng file đó làm `--config` cho từng
bước — `_resolve_run_id()` của `qshield_ai`/`qshield_quantum` đã được sửa (thêm, không đổi hành vi
mặc định) để ưu tiên đọc khóa này trước khi tự sinh.

Ở `artifacts.mode: dev` (mặc định trong suốt sprint này), `ArtifactPaths` không phụ thuộc `run_id`
để dựng đường dẫn — nên không cần tiêm gì cả, dùng thẳng config gốc cho mọi bước.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from qshield_contracts.config import Config
from qshield_contracts.enums import ArtifactMode
from qshield_contracts.paths import ArtifactPaths
from qshield_contracts.runs import RunContext


def resolve_pipeline_run_id(cfg: Config) -> str | None:
    """`dev` không cần run_id (đường dẫn cố định); `runs` sinh MỘT run_id cho toàn bộ pipeline."""
    mode = ArtifactMode(str(cfg.get("artifacts", {}).get("mode", "dev")))
    if mode == ArtifactMode.DEV:
        return None
    return f"run_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"


class PipelineRunContext:
    """Bọc `ArtifactPaths` + `RunContext` ở CẤP PIPELINE — chỉ dùng để: (1) sinh một `run_id`
    dùng chung, (2) có logger ghi vào CÙNG `logs.txt` mà từng bước cũng ghi vào (FileHandler mở
    append, nên không đè lẫn nhau), (3) tạo config đã tiêm `run_id` cho từng bước gọi.

    KHÔNG gọi `write_config_snapshot()`/`write_metrics()` ở đây — mỗi bước đã tự ghi
    `config.json`/`metrics.json` của chính nó vào cùng `run_root`; gọi lại ở cấp pipeline sẽ ĐÈ mất
    chi tiết bước cuối cùng thay vì bổ sung thông tin.
    """

    def __init__(self, cfg: Config) -> None:
        self.run_id = resolve_pipeline_run_id(cfg)
        self.paths = ArtifactPaths(cfg, run_id=self.run_id)
        # `Stage.RISK` chỉ để có MỘT stage hợp lệ cho `ensure()` — pipeline chỉ cần `run_root`
        # tồn tại để ghi logs.txt, không quan tâm thư mục stage cụ thể nào.
        self.paths.run_root.mkdir(parents=True, exist_ok=True)
        self._run_context = RunContext(cfg, self.paths)
        self.logger = self._run_context.logger("pipeline")

    def resolve_config_path(self, cfg: Config, original_config_path: Path) -> Path:
        """Trả về đường dẫn config dùng làm `--config` cho MỌI bước.

        `dev` mode: trả nguyên `original_config_path` (không cần tiêm gì). `runs` mode: ghi bản
        config đã merge (không còn `includes`) kèm khóa `run_id` ra file tạm trong `run_root`.
        """
        if self.run_id is None:
            return original_config_path
        merged: dict[str, Any] = dict(cfg)
        merged["run_id"] = self.run_id
        out_path = self.paths.run_root / "_pipeline_resolved_config.yaml"
        out_path.write_text(
            yaml.safe_dump(merged, allow_unicode=True), encoding="utf-8"
        )
        return out_path
