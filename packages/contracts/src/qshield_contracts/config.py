# Đỗ Ngọc Tân - đọc & gộp configs/*.yaml qua includes — nơi DUY NHẤT trong repo được mở file yaml.
"""`Config` — nơi DUY NHẤT trong repo được phép `open()`/`yaml.safe_load` trên `configs/*.yaml`.

Port thẳng từ `qshield_data/_config_stub.py::load_config` (đã chạy thật trên dữ liệu thật, xem
`packages/data/src/qshield_data/cli.py`) — không đổi hành vi merge, chỉ đổi chỗ sống. `_config_stub`
bị xóa sau khi module này thay thế nó (plan-contracts.md §4).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class WorkflowRuntime:
    """Resolved dimensions for a four-level downstream workflow run.

    The development path may use fewer candidates than the baseline target, but the encoding
    relationship remains invariant: two bits per candidate and one structured objective sample
    for the intercept, every main effect, and every pairwise interaction.
    """

    profile_id: str
    profile_status: str
    candidate_count: int
    bits_per_candidate: int
    total_decision_bits: int
    structured_sample_count: int
    action_levels_pct: tuple[int, ...]

    @property
    def minimum_structured_samples(self) -> int:
        """Return ``1 + n + nC2`` for ``n`` decision bits."""
        return (
            1
            + self.total_decision_bits
            + (self.total_decision_bits * (self.total_decision_bits - 1) // 2)
        )

    def validate(self) -> None:
        if self.candidate_count <= 0:
            raise ValueError("runtime.candidate_count must be positive.")
        if self.bits_per_candidate <= 0:
            raise ValueError("runtime.bits_per_candidate must be positive.")
        expected_bits = self.candidate_count * self.bits_per_candidate
        if self.total_decision_bits != expected_bits:
            raise ValueError(
                "runtime.total_decision_bits="
                f"{self.total_decision_bits}, expected {expected_bits} from "
                "candidate_count * bits_per_candidate."
            )
        if self.structured_sample_count < self.minimum_structured_samples:
            raise ValueError(
                "runtime.structured_sample_count="
                f"{self.structured_sample_count}, requires at least "
                f"{self.minimum_structured_samples} for {self.total_decision_bits} bits."
            )
        if self.action_levels_pct != (0, 10, 20, 30):
            raise ValueError(
                "Four-level workflow requires action_levels_pct=[0, 10, 20, 30]."
            )


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

    @classmethod
    def load_profiled(
        cls,
        base_yaml: Path,
        profile_yaml: Path,
        override_yaml: Path | None = None,
    ) -> Config:
        """Deep-merge base, product profile, then optional explicit run overrides.

        The regular base config remains flat for backward compatibility. Nested profile sections
        are preserved, while an override may replace only the runtime dimensions or provisional
        financial values it declares. This is the required loader for workflow-profile runs.
        """
        merged: dict[str, Any] = dict(cls.load(base_yaml))
        _deep_merge(merged, _load_yaml(Path(profile_yaml)))
        if override_yaml is not None:
            _deep_merge(merged, _load_yaml(Path(override_yaml)))
        return cls(merged)

    def workflow_runtime(self) -> WorkflowRuntime:
        """Resolve and validate generic downstream dimensions from ``profile``/``runtime``."""
        profile = self.get("profile", {}) or {}
        runtime = self.get("runtime", {}) or {}
        result = WorkflowRuntime(
            profile_id=str(profile.get("id", "")),
            profile_status=str(profile.get("status", "")),
            candidate_count=int(runtime.get("candidate_count", 0)),
            bits_per_candidate=int(runtime.get("bits_per_candidate", 0)),
            total_decision_bits=int(runtime.get("total_decision_bits", 0)),
            structured_sample_count=int(runtime.get("structured_sample_count", 0)),
            action_levels_pct=tuple(
                int(value) for value in runtime.get("action_levels_pct", [])
            ),
        )
        if not result.profile_id:
            raise ValueError("profile.id is required for downstream workflow runs.")
        if not result.profile_status:
            raise ValueError("profile.status is required for downstream workflow runs.")
        result.validate()
        return result


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    """Recursively merge mappings while replacing scalar/list leaves."""
    for key, value in incoming.items():
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _deep_merge(current, value)
        else:
            target[key] = value
