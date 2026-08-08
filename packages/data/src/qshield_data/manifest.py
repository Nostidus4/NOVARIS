# Nguyễn Đỗ Minh Anh - hash + version → data/metadata/data_manifest.json.
"""Data Manifest — port từ `CLEAN.ipynb` Cell 6 (`sha256_of_file`, `to_utc_date`) và Cell 55
(data manifest JSON).

`build_manifest`/`write_manifest` không tự sinh `run_id` hay ghi `config.json`/`logs.txt` — theo
CLAUDE.md quy tắc 13, chỉ `RunContext` (`packages/contracts`) mới được ghi metadata run-level. Đây
là manifest cấp *data package* (data version, file hash, row counts), không phải run manifest của
toàn pipeline.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def _sha256_of_file(path: Path) -> str:
    """Tính SHA-256 checksum của file theo chunk 1MB — dùng để version raw/processed data."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_utc_date(x: Any) -> str:
    """Chuẩn hoá về `YYYY-MM-DD`."""
    return pd.to_datetime(x).strftime("%Y-%m-%d")


def _file_info(path: Path, data_root: Path) -> dict[str, Any] | None:
    """Trả `{path, sha256, size_bytes, modified_at}` tương đối so với `data_root.parent`, hoặc
    `None` nếu file không tồn tại (vd bước tạo ra nó bị skip/fail)."""
    path = Path(path)
    if not path.exists():
        return None
    data_root = Path(data_root)
    try:
        rel_path = str(path.relative_to(data_root.parent))
    except ValueError:
        rel_path = str(path)
    return {
        "path": rel_path,
        "sha256": _sha256_of_file(path),
        "size_bytes": path.stat().st_size,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime)
        .astimezone()
        .isoformat(),
    }


def build_manifest(
    run_id: str,
    data_version: str,
    universe_version: str,
    universe_as_of: str,
    files: dict[str, Path],
    row_counts: dict[str, int],
    splits_config: dict[str, Any],
    eligibility_config: dict[str, Any],
    quality_gate_pass: bool,
    index_symbol_used: str | None,
    index_source_used: str | None,
    data_root: Path,
) -> dict[str, Any]:
    """Xây manifest dict cho một lần chạy `qshield_data` (không phải run manifest toàn pipeline).

    `files`: tên logic → path (vd `{"prices_adjusted": .../prices_adjusted.parquet}`).
    `splits_config`: `{"market": {"train": [start, end], "validation": [...], "test": [...]},
    "asset": {...}}` — khớp `configs/base.yaml` train/validation/test date_range.
    """
    return {
        "run_id": run_id,
        "data_version": data_version,
        "universe_version": universe_version,
        "universe_as_of": universe_as_of,
        "created_at": datetime.now().astimezone().isoformat(),
        "sources": ["YF_PRICES", "DNSE_PRICES", "VNSTOCK_PRICES", "VNSTOCK_INDEX"],
        "index_symbol_used": index_symbol_used,
        "index_source_used": index_source_used,
        "splits_config": splits_config,
        "eligibility_config": eligibility_config,
        "quality_gate_status": "PASS" if quality_gate_pass else "FAIL",
        "files": {name: _file_info(path, data_root) for name, path in files.items()},
        "row_counts": row_counts,
    }


def write_manifest(manifest: dict[str, Any], out_path: Path) -> Path:
    """Ghi `data/metadata/data_manifest.json` (`ensure_ascii=False` để giữ tiếng Việt)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return out_path
